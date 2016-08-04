# -*- rpm-spec -*-

# The full kernel uname version
%define uname         3.10.0+0

%ifarch %{ix86}
%define target       %{_target_cpu}
%define arch	     i386
%endif

%ifarch x86_64
%define target       %{_target_cpu}
%define arch         %{_target_cpu}
%endif

%define COMMON_MAKEOPTS %{?_smp_mflags}
%define DEFINE_MAKEOPTS \
	ARCH=%{arch}; \
	unset CROSS_COMPILE; \
 	case ${ARCH} in \
	    *64) [ $(uname -m) = ${ARCH} ] || CROSS_COMPILE=x86_64-linux- ;; \
	esac ; \
	MAKEOPTS="%{COMMON_MAKEOPTS} ARCH=${ARCH} CROSS_COMPILE=${CROSS_COMPILE}"


#
# First the general kernel required versions as per
# Documentation/Changes
#
%define kernel_dot_org_conflicts  ppp < 2.4.3-3, isdn4k-utils < 3.2-32, nfs-utils < 1.0.7-12, e2fsprogs < 1.37-4, util-linux < 2.12, jfsutils < 1.1.7-2, reiserfs-utils < 3.6.19-2, xfsprogs < 2.6.13-4, procps < 3.2.5-6.3, oprofile < 0.9.1-2

#
# Then a series of requirements that are distribution specific, either
# because we add patches for something, or the older versions have
# problems with the newer kernel or lack certain things that make
# integration in the distro harder than needed.
#
%define package_conflicts  initscripts < 7.23, udev < 145-11, iptables < 1.3.2-1, ipw2200-firmware < 2.4, iwl4965-firmware < 228.57.2, selinux-policy-targeted < 1.25.3-14, squashfs-tools < 4.0, wireless-tools < 29-3, bfa-firmware < 3.0.3.1

#
# Packages that need to be installed before the kernel is, because the %post
# scripts use them.
#
%define kernel_prereq  fileutils, module-init-tools, initscripts >= 8.11.1-1, grubby >= 7.0.4-1, dracut >= 001-7

#
# don't use RPM's internal dependency generator, instead
# just use our magic one that finds the versions of kernel modules for
# provides and don't do any requires
# (we used to just turn off AutoReqProv on all packages)
#
%define _use_internal_dependency_generator 0
%define __find_provides %{nil}
%define __find_requires %{nil}

Name: kernel
Vendor: Citrix Systems, Inc.
License: GPLv2
Version: 3.10.96
Release: 367.382019
ExclusiveArch: noarch i686 x86_64
ExclusiveOS: Linux
Summary: The Linux kernel built for Xen.
BuildRequires: module-init-tools, patch >= 2.5.4, bash >= 2.03, sh-utils, tar
BuildRequires: bzip2, findutils, gzip, m4, perl, make >= 3.78
BuildRequires: gcc >= 2.96-98, binutils >= 2.12, redhat-rpm-config >= 8.0.32.1
BuildRequires: bc
Provides: kernel-uname-r = %{uname}
Autoreqprov: no
Requires(pre): %{kernel_prereq}
Conflicts: %{kernel_dot_org_conflicts}
Conflicts: %{package_conflicts}

Source0: http://hg.uk.xensource.com/git/carbon/trunk-ring0/linux-3.x.git/snapshot/refs/heads/master#/linux-3.x.tar.bz2
Source1: macros.kernel

%description
This package provides the Linux kernel for privileged and unprivileged domains.

%package headers
Summary: Header files for the Linux kernel for use by glibc
Group: Development/System
Obsoletes: glibc-kernheaders
Provides: kernel-headers = %{uname}
Conflicts: kernel-headers < %{uname}

%description headers
This package provides the C header files that specify the interface
between the Linux kernel and userspace libraries & programs. The
header files define structures and constants that are needed when
building most standard programs. They are also required when
rebuilding the glibc package.


%package devel
Summary: Development package for building kernel modules to match the xen kernel.
Group: System Environment/Kernel
AutoReqProv: no
Provides: kernel-devel = %{uname}

%description devel
This package provides kernel headers and makefiles sufficient to build modules
against the %{uname} kernel.


#%package doc
#Summary: Various documentation bits found in the kernel source.
#Group: Documentation
#
#%description doc
#This package contains documentation files from the kernel
#source. Various bits of information about the Linux kernel and the
#device drivers shipped with it are documented in these files.
#
#You'll want to install this package if you need a reference to the
#options that can be passed to Linux kernel modules at load time.

%prep

%autosetup -p1

%{DEFINE_MAKEOPTS}
make ${MAKEOPTS} mrproper
cp -f buildconfigs/linux-defconfig_xen_%{target} .config

%build

# This override tweaks the kernel makefiles so that we run debugedit on an
# object before embedding it.  When we later run find-debuginfo.sh, it will
# run debugedit again.  The edits it does change the build ID bits embedded
# in the stripped object, but repeating debugedit is a no-op.  We do it
# beforehand to get the proper final build ID bits into the embedded image.
# This affects the vDSO images in vmlinux, and the vmlinux image in bzImage.
export AFTER_LINK='sh -xc "/usr/lib/rpm/debugedit -b $$RPM_BUILD_DIR -d /usr/src/debug -i $@ > $@.id"'

#cd linux-3.x-%{version}
%{DEFINE_MAKEOPTS}
make ${MAKEOPTS} silentoldconfig
if grep -q ^CONFIG_MODULES=y$ .config ; then
    mkmodules=modules
else
    mkmodules=
fi

%{?cov_wrap} make ${MAKEOPTS} bzImage $mkmodules

%install

#cd linux-3.x-%{version}
%{DEFINE_MAKEOPTS}
# Install kernel
install -d -m 755 $RPM_BUILD_ROOT/boot
install -m 644 .config $RPM_BUILD_ROOT/boot/config-%{uname}
install -m 644 System.map $RPM_BUILD_ROOT/boot/System.map-%{uname}
install -m 644 arch/x86/boot/bzImage $RPM_BUILD_ROOT/boot/vmlinuz-%{uname}

install -d -m 755 $RPM_BUILD_ROOT/lib/modules/%{uname}
if grep -q ^CONFIG_MODULES=y$ .config ; then
    # Install modules
    make ${MAKEOPTS} INSTALL_MOD_PATH=$RPM_BUILD_ROOT modules_install
    # mark modules executable so that strip-to-file can strip them
    find $RPM_BUILD_ROOT/lib/modules/%{uname} -name "*.ko" -type f | xargs chmod u+x
fi

# Save debuginfo
install -d -m 755 $RPM_BUILD_ROOT/usr/lib/debug/lib/modules/%{uname}
install -m 755 vmlinux $RPM_BUILD_ROOT/usr/lib/debug/lib/modules/%{uname}

# Install -headers files
make ${MAKEOPTS} INSTALL_HDR_PATH=$RPM_BUILD_ROOT/usr headers_install

# Install -devel files
install -d -m 755 $RPM_BUILD_ROOT/usr/src/kernels/%{uname}-%{target}
install -d -m 755 $RPM_BUILD_ROOT%{_rpmconfigdir}/macros.d
install -m 644 %{SOURCE1} $RPM_BUILD_ROOT%{_rpmconfigdir}/macros.d

# Setup -devel links correctly
SOURCE=/usr/src/kernels/%{uname}-%{target}
rm -f $RPM_BUILD_ROOT/lib/modules/%{uname}/build
rm -f $RPM_BUILD_ROOT/lib/modules/%{uname}/source
ln -sf $SOURCE $RPM_BUILD_ROOT/lib/modules/%{uname}/source
ln -sf $SOURCE $RPM_BUILD_ROOT/lib/modules/%{uname}/build

install -d -m 755 $RPM_BUILD_ROOT${SOURCE}/arch/x86/kernel

cp --parents `find  -type f -name "Makefile*" -o -name "Kconfig*"` $RPM_BUILD_ROOT${SOURCE}
if [ -e Module.symvers ]; then
    install -m 644 Module.symvers $RPM_BUILD_ROOT${SOURCE}
fi
cp System.map $RPM_BUILD_ROOT${SOURCE}
if [ -s Module.markers ]; then
      cp Module.markers $RPM_BUILD_ROOT${SOURCE}
fi
# then drop all but the needed Makefiles/Kconfig files
rm -rf $RPM_BUILD_ROOT${SOURCE}/Documentation
rm -rf $RPM_BUILD_ROOT${SOURCE}/scripts
rm -rf $RPM_BUILD_ROOT${SOURCE}/include
install -m 644 arch/x86/kernel/asm-offsets.s $RPM_BUILD_ROOT${SOURCE}/arch/x86/kernel || :
install -m 644 .config $RPM_BUILD_ROOT${SOURCE}
install -m 644 .kernelrelease $RPM_BUILD_ROOT${SOURCE} || :
cp -a scripts $RPM_BUILD_ROOT${SOURCE}
cp -a arch/x86/scripts $RPM_BUILD_ROOT${SOURCE}/arch/x86 || :
cp -a arch/x86/*lds $RPM_BUILD_ROOT${SOURCE}/arch/x86 || :
rm -f $RPM_BUILD_ROOT${SOURCE}/scripts/*.o
rm -f $RPM_BUILD_ROOT${SOURCE}/scripts/*/*.o

if [ -d arch/x86/include ] ; then
    cp -a --parents arch/x86/include $RPM_BUILD_ROOT${SOURCE}
fi
if [ -d arch/x86/syscalls ] ; then
    cp -a --parents arch/x86/syscalls $RPM_BUILD_ROOT${SOURCE}
fi

cp -a include $RPM_BUILD_ROOT${SOURCE}/include

rm -f $RPM_BUILD_ROOT${SOURCE}/include/Kbuild
cp -a include/generated/uapi/linux/version.h $RPM_BUILD_ROOT${SOURCE}/include/linux/
cp -a include/generated/autoconf.h $RPM_BUILD_ROOT${SOURCE}/include/linux/

# Copy .config to include/config/auto.conf so "make prepare" is unnecessary.
cp $RPM_BUILD_ROOT${SOURCE}/.config $RPM_BUILD_ROOT${SOURCE}/include/config/auto.conf

# Make sure the Makefile, .config, auto.conf, autoconf.h and version.h have a matching
# timestamp so that external modules can be built
touch -r $RPM_BUILD_ROOT${SOURCE}/Makefile $RPM_BUILD_ROOT${SOURCE}/.config
touch -r $RPM_BUILD_ROOT${SOURCE}/Makefile $RPM_BUILD_ROOT${SOURCE}/include/config/auto.conf
touch -r $RPM_BUILD_ROOT${SOURCE}/Makefile $RPM_BUILD_ROOT${SOURCE}/include/linux/autoconf.h
touch -r $RPM_BUILD_ROOT${SOURCE}/Makefile $RPM_BUILD_ROOT${SOURCE}/include/linux/version.h
touch -r $RPM_BUILD_ROOT${SOURCE}/Makefile $RPM_BUILD_ROOT${SOURCE}/include/generated/autoconf.h
touch -r $RPM_BUILD_ROOT${SOURCE}/Makefile $RPM_BUILD_ROOT${SOURCE}/include/generated/uapi/linux/version.h

# Firmware is provided by the linux-firmware package.
rm -rf $RPM_BUILD_ROOT/lib/firmware

find $RPM_BUILD_ROOT -name ..install.cmd -type f -delete

%post
short_uname=$(echo %{uname} | awk -F '[.]' '{print $1 "." $2}')

if [ -e /boot/vmlinuz-$short_uname-xen ]; then
  /sbin/new-kernel-pkg --update --mkinitrd --depmod %{uname}
else
  /sbin/new-kernel-pkg --install --make-default --mkinitrd --depmod %{uname}
fi

ln -sf vmlinuz-%{uname} /boot/vmlinuz-$short_uname-xen
ln -sf initrd-%{uname}.img /boot/initrd-$short_uname-xen.img

%preun
if [ "$1" = "0" ]; then
  /sbin/new-kernel-pkg --remove --rminitrd --rmmoddep %{uname}
fi

%triggerin -- xen-hypervisor
new-kernel-pkg --install %{uname}

%files
%defattr(-,root,root)
/boot/vmlinuz-%{uname}
/boot/System.map-%{uname}
/boot/config-%{uname}
%dir /lib/modules/%{uname}
/lib/modules/%{uname}/kernel
/lib/modules/%{uname}/modules.order
/lib/modules/%{uname}/modules.builtin
%exclude /lib/modules/%{uname}/modules.alias
%exclude /lib/modules/%{uname}/modules.alias.bin
%exclude /lib/modules/%{uname}/modules.builtin.bin
%exclude /lib/modules/%{uname}/modules.dep
%exclude /lib/modules/%{uname}/modules.dep.bin
%exclude /lib/modules/%{uname}/modules.devname
%exclude /lib/modules/%{uname}/modules.softdep
%exclude /lib/modules/%{uname}/modules.symbols
%exclude /lib/modules/%{uname}/modules.symbols.bin

%files headers
%defattr(-,root,root)
/usr/include

%files devel
%defattr(-,root,root)
/lib/modules/%{uname}/build
/lib/modules/%{uname}/source
%verify(not mtime) /usr/src/kernels/%{uname}-%{target}
%{_rpmconfigdir}/macros.d/macros.kernel

%changelog
* Wed Sep 25 2013 Malcolm Crossley <malcolm.crossley@eu.citrix.com> - 3.10
- Synced with elrepo kernel-ml packaging style
* Thu Mar 29 2012 Simon Rowe <simon.rowe@eu.citrix.com> - 3.3.0-rc3
- Packaged for XenServer
