# -*- coding: utf-8 -*-
{
    'name': "Sale Proposal",

    'summary': """
        With this module you will able to manage a proposal of
         a list of product to a customer.""",

    'description': """
        
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'sale', 'sale_management', 'website'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/mail_template_data.xml',
        'views/sale_proposal_views.xml',
        'views/sale_proposal_template.xml',
        'views/thankyou_template.xml',
        'views/assets.xml',
    ],
}
