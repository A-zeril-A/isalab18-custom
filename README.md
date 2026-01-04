# ISALAB Odoo 18 Custom Modules

Custom addons and configuration for Odoo 18 (migrated from Odoo 17).

## 📁 Structure

```
isalab18-custom/
├── custom_addons/           # Custom modules (migrated)
├── custom_3rdP_addons/      # Third-party modules
│   ├── module_from_oca/
│   └── module_from_other_vendor/
├── isa18.cfg.template       # Configuration template
└── README.md
```

## 🚀 Setup

```bash
# Clone into /opt/odoo/
cd /opt/odoo
git clone https://github.com/A-zeril-A/isalab18-custom.git isalab18-custom

# Run setup script (from isalab15-custom)
cd /opt/odoo/isalab15-custom/scripts
sudo ./setup_odoo_version.sh 18
```

## 🔄 Migration from v17

Use the migration backup from Odoo 17.

## 🚀 Start Odoo 18

```bash
sudo -u odoo -H /opt/odoo/isalab18/venv_isalab18/bin/python3 \
  /opt/odoo/isalab18/odoo-bin -c /opt/odoo/isalab18/config/isa18.cfg
```

Web: http://SERVER_IP:8018

