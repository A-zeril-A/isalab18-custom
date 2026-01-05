# -*- coding: utf-8 -*-
{
    'name': "Custom Limited CRM Log Note and Views",

    'summary': "Restrict log notes in CRM and provide customized field visibility for general users.",

    'description': """
Custom Limited CRM Log Note and Views
=====================================

This module customizes the CRM log notes by limiting the displayed information 
to only the opportunity name and customer name, preventing unnecessary details 
from appearing in the chatter. It also adds restrictions to some fields, 
making them visible only to specific groups, such as 'CRM Full Access'.

Features
--------
* Limits tracked field changes to partner_id and stage_id only
* Hides expected_revenue, recurring_revenue, and related financial fields 
  from users without 'CRM Full Access' group
* Applies restrictions across all views: Form, Kanban, List, Pivot, 
  Calendar, Activity, and Quick Create

Odoo 18 Compatibility
---------------------
* Updated XPath expressions for new form structure
* Updated kanban view for new card template structure (t-name="card")
* Uses _track_get_fields() override for tracking customization
* Properly handles field declarations in kanban templates
* Compatible with mail.tracking.duration.mixin
    """,

    'author': "A_zeril_A",
    'website': "https://github.com/ImanGholamii/Odoo_CRM_Limited_views",

    'category': 'CRM',
    'version': '18.0.2.0.1',

    'depends': ['base', 'crm', 'mail'],

    'data': [
        'security/security.xml',
        'views/crm_lead_views.xml',
        'views/crm_lead_kanban_inherit_views.xml',
        'views/crm_lead_inherit_views.xml',
    ],
    
    'demo': [],
    
    'icon': 'custom_limited_crm_log_note_and_views/static/description/icon.png',
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
