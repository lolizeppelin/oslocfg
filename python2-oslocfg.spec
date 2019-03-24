%include %{_rpmconfigdir}/macros.python

%global debug_package %{nil}
%define proj_name oslocfg
%define _release 2

Name:           python2-%{proj_name}
Version:        1.0.0
Release:        %{_release}%{?dist}
Summary:        oslo cfg copy from openstack
Group:          Development/Libraries
License:        MPLv1.1 or GPLv2
URL:            http://github.com/Lolizeppelin/%{proj_name}
Source0:        %{proj_name}-%{version}.tar.gz
BuildArch:      noarch

BuildRequires:  python2 >= 2.7
BuildRequires:  python2-setuptools >= 40

Requires:       python2 >= 2.7
Requires:       python2-netaddr >= 0.7.5
Requires:       python2-six >= 1.9.0


%description
config utils copy from openstack

%prep
%setup -q -n %{proj_name}-%{version}
rm -rf %{proj_name}.egg-info

%build
CFLAGS="$RPM_OPT_FLAGS" %{__python} setup.py build

%install
%{__rm} -rf %{buildroot}
%{__python2} setup.py install -O1 --skip-build --root %{buildroot}

%clean
%{__rm} -rf %{buildroot}


%files
%defattr(-,root,root,-)
%{py_sitedir}/%{proj_name}/*
%dir %{py_sitedir}/%{proj_name}-%{version}-*.egg-info/
%{py_sitedir}/%{proj_name}-%{version}-*.egg-info/*
#%{py_sitedir}/%{proj_name}/*
#%{python2_sitearch}/%{proj_name}/*
#%{python2_sitearch}/%{proj_name}-%{version}-*.egg-info/*
#%dir %{python2_sitearch}/%{proj_name}-%{version}-*.egg-info/
%doc README.rst
%doc doc/*

%changelog
* Fri Mar 15 2019 Lolizeppelin <lolizeppelin@gmail.com> - 1.0.0
- Initial Package