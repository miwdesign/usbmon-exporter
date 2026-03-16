%undefine __pythondist_requires

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
python3.12 -m pip install --target %{buildroot}%{_datadir}/%{name}/vendor prometheus-client

install -D -p -m 0644 %{SOURCE1} %{buildroot}%{_unitdir}/%{name}.service
install -D -p -m 0644 %{SOURCE2} %{buildroot}%{_modulesloaddir}/%{name}.conf
install -D -p -m 0644 %{SOURCE3} %{buildroot}%{_sysconfdir}/sysconfig/%{name}
install -D -p -m 0644 %{SOURCE4} %{buildroot}%{_udevrulesdir}/99-usbmon.rules

mkdir -p %{buildroot}/var/lib/usbmon-exporter

%pre
getent group miw >/dev/null || groupadd -r miw
getent passwd usbmon >/dev/null || useradd -r -g miw -s /sbin/nologin -d /var/lib/usbmon-exporter usbmon

%post
%systemd_post %{name}.service
if [ $1 -eq 1 ]; then
    /usr/bin/systemctl start %{name}.service
fi
chown -R usbmon:miw /var/lib/usbmon-exporter

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

%changelog
* Thu Mar 5 2026 Ariel Donovan <arield@miwcorp.com> - 0.2.0-3
- Add request latency metric
- Add RPM build system
