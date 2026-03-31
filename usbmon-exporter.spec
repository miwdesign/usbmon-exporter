%undefine __pythondist_requires
%global python3 /usr/bin/python3.12
%global __python3 /usr/bin/python3.12

Name:           usbmon-exporter
Version:        0.2.0
Release:        3%{?dist}
Summary:        Prometheus exporter for usbmon

License:        MIT
URL:            https://github.com/miwdesign/usbmon-exporter
Source0:        %{name}-%{version}.tar.gz
Source1:        %{name}.service
Source2:        %{name}.conf
Source3:        %{name}.sysconfig
Source4:        99-usbmon.rules
Source5:        usbmon-exporter-sysusers.conf

BuildArch:      noarch

BuildRequires:  pyproject-rpm-macros
BuildRequires:  python3.12-devel
BuildRequires:  python3.12-pip
BuildRequires:  python3.12-setuptools >= 68.0.0
BuildRequires:  python3.12-wheel
BuildRequires:  systemd-rpm-macros

Requires:       python3.12
Requires:       systemd

%{?systemd_requires}
Requires:       shadow-utils

%description
usbmon-exporter is a Prometheus exporter that captures USB device metrics
using the Linux Kernel usbmon interface.

%prep
%autosetup

%build
%pyproject_wheel

%install
%pyproject_install
%pyproject_save_files usbmon_exporter

mkdir -p %{buildroot}%{_datadir}/%{name}/vendor
python3.12 -m pip install --target %{buildroot}%{_datadir}/%{name}/vendor --no-compile prometheus-client

# Remove shebangs on nonexecutable .py files in vendor directory to keep rpmlint happy
find %{buildroot}%{_datadir}/%{name}/vendor -name "*.py" -exec sed -i '/^#!\/usr\/bin\/env python/d' {} +
# Delete vendored zero-sized files to keep rpmlint happy
find %{buildroot}%{_datadir}/%{name}/vendor -size 0 -delete

install -D -p -m 0644 %{SOURCE1} %{buildroot}%{_unitdir}/%{name}.service
install -D -p -m 0644 %{SOURCE2} %{buildroot}%{_modulesloaddir}/%{name}.conf
install -D -p -m 0644 %{SOURCE3} %{buildroot}%{_sysconfdir}/sysconfig/%{name}
install -D -p -m 0644 %{SOURCE4} %{buildroot}%{_udevrulesdir}/99-usbmon.rules
install -D -p -m 0644 %{SOURCE5} %{buildroot}%{_sysusersdir}/%{name}.conf
mkdir -p %{buildroot}/var/lib/usbmon-exporter

%pre
%sysusers_create %{SOURCE5}

%post
%systemd_post %{name}.service
if [ $1 -eq 1 ]; then
    systemctl start %{name}.service
fi

%preun
%systemd_preun %{name}.service

%postun
%systemd_postun_with_restart %{name}.service

%files -f %{pyproject_files}
%license LICENSE.txt
%doc README.md
%{_bindir}/usbmon_exporter
%{_unitdir}/%{name}.service
%{_modulesloaddir}/%{name}.conf
%{_datadir}/%{name}
%config(noreplace) %{_sysconfdir}/sysconfig/%{name}
%dir %attr(0755, usbmon, miw) /var/lib/usbmon-exporter
%{_udevrulesdir}/99-usbmon.rules
%{_sysusersdir}/%{name}.conf

%changelog
* Thu Mar 5 2026 Ariel Donovan <arield@miwcorp.com> - 0.2.0-3
- Add request latency metric
- Add RPM build system
