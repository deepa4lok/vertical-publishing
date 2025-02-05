# -*- coding: utf-8 -*-
# Copyright 2017 Willem hulshof - <w.hulshof@magnus.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models, _

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'


    group_sale_customer_contact = fields.Boolean("Contact Person", implied_group='sale_advertising_order.group_ads_contact_person')
    show_actual_unit_price = fields.Boolean("Show actual unit price", related="company_id.show_actual_unit_price", readonly=False)
    sao_show_discount_reason = fields.Boolean(related="company_id.sao_show_discount_reason", readonly=False)
    sao_orderline_order_field_id = fields.Many2one(related="company_id.sao_orderline_order_field_id", readonly=False)
    sao_split_line_state = fields.Selection(related="company_id.sao_split_line_state", readonly=False)
