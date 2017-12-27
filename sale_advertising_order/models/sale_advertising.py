# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2016 Magnus (<http://www.magnus.nl>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import json
from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError
from datetime import datetime, timedelta


class SaleOrder(models.Model):
    _inherit = ["sale.order"]

    @api.depends('order_line.price_total', 'order_line.computed_discount', 'partner_id')
    def _amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        super(SaleOrder, self)._amount_all()
        for order in self.filtered('advertising'):
            amount_untaxed = amount_tax = max_cdiscount = 0.0
            cdiscount = []
            ver_tr_exc = False
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                cdiscount.append(line.computed_discount)
                if cdiscount:
                    max_cdiscount = max(cdiscount)
                if order.company_id.tax_calculation_rounding_method == 'round_globally':
                    if not line.multi_line:
                        price = line.acual_unit_price * (1 - (line.discount or 0.0) / 100.0)
                        taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty,
                                                        product=line.product_id, partner=order.partner_id)
                        amount_tax += sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
                    else:
                        price = line.subtotal_before_agency_disc * (1 - (line.discount or 0.0) / 100.0)
                        taxes = line.tax_id.compute_all(price, line.order_id.currency_id, quantity=1,
                                                        product=line.product_id, partner=order.partner_id)
                        amount_tax += sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
                else:
                    amount_tax += line.price_tax
                if order.company_id.verify_order_setting != -1.00 and order.company_id.verify_order_setting < amount_untaxed or order.company_id.verify_discount_setting < max_cdiscount:
                    ver_tr_exc = True

            order.update({
                'amount_untaxed': order.pricelist_id.currency_id.round(amount_untaxed),
                'amount_tax': order.pricelist_id.currency_id.round(amount_tax),
                'amount_total': amount_untaxed + amount_tax,
                'ver_tr_exc': ver_tr_exc,
                'max_discount': max_cdiscount,
            })


    state = fields.Selection([
        ('draft', 'Quotation'),
        ('submitted', 'Submitted for Approval'),
        ('approved1', 'Approved by Sales Support'),
        ('approved2', 'Approved by Traffic'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sale Order'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
        ], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange', default='draft')

    published_customer = fields.Many2one('res.partner', 'Advertiser', domain=[('customer','=',True)])
    advertising_agency = fields.Many2one('res.partner', 'Advertising Agency', domain=[('customer','=',True)])
    nett_nett = fields.Boolean('Netto Netto Deal', default=False)
    customer_contact = fields.Many2one('res.partner', 'Payer Contact Person', domain=[('customer','=',True)])
    traffic_employee = fields.Many2one('res.users', 'Traffic Employee',)
    traffic_comments = fields.Text('Traffic Comments')
    traffic_appr_date = fields.Date('Traffic Confirmation Date', index=True, help="Date on which sales order is confirmed bij Traffic.")
    opportunity_subject = fields.Char('Opportunity Subject', size=64,
                          help="Subject of Opportunity from which this Sales Order is derived.")
    partner_acc_mgr = fields.Many2one(related='published_customer.user_id', relation='res.users', string='Account Manager', store=True , readonly=True)
    date_from = fields.Date(compute=lambda *a, **k: {}, string="Date from")
    date_to = fields.Date(compute=lambda *a, **k: {}, string="Date to")
    ver_tr_exc = fields.Boolean(string='Verification Treshold', store=True, readonly=True, compute='_amount_all', track_visibility='always')
    advertising = fields.Boolean('Advertising', default=False)
    max_discount = fields.Integer(compute='_amount_all', track_visibility='always', store=True, string="Maximum Discount")



    # overridden:
    @api.multi
    @api.onchange('partner_id', 'published_customer', 'advertising_agency')
    def onchange_partner_id(self):
        """
        Update the following fields when the partner is changed:
        - Pricelist
        - Payment term
        - Invoice address
        - Delivery address
        """

        # Advertiser:
        if self.advertising:
            if self.published_customer:
                self.partner_id = self.published_customer.id
            if self.advertising_agency:
                self.partner_id = self.advertising_agency

        super(SaleOrder, self).onchange_partner_id()

        if not self.partner_id:
            self.update({
                'customer_contact': False
            })
            return

        if self.partner_id.type == 'contact':
            contact = self.env['res.partner'].search([('is_company','=', False),('type','=', 'contact'),('parent_id','=', self.partner_id.id)])
            if len(contact) >=1:
                contact_id = contact[0]
            else:
                contact_id = False
        else:
            addr = self.partner_id.address_get(['delivery', 'invoice'])
            contact_id = addr['contact']
        if not self.partner_id.is_company and not self.partner_id.parent_id:
            contact_id = self.partner_id
        # Not sure about this!
        self.user_id = self._uid
        self.customer_contact = contact_id
        if self.order_line:
            warning = {'title':_('Warning'),
                                 'message':_('Changing the Customer can have a change in Agency Discount as a result.'
                                             'This change will only show after saving the order!'
                                             'Before saving the order the order lines and the total amounts may therefor'
                                             'show wrong values.')}
            return {'warning': warning}




    '''@api.multi
    def update_line_discount(self):
        self.ensure_one()
        discount = self.partner_id.agency_discount or 0.0
        if self.nett_nett:
            discount = 0.0
        fiscal_position = self.partner_id.property_account_position_id

        for line in self.order_line:
            tax = []
            if fiscal_position:
                tax = fiscal_position.map_tax(line.product_id.taxes_id, line.product_id, self.partner_id).ids
            vals = {}
            vals['discount'] = discount
            vals['tax_id'] = [(6,0,tax)]

            line.write(vals)
        return True'''

    @api.multi
    def action_submit(self):
        orders = self.filtered(lambda s: s.state in ['draft'])
        for o in orders:
            if not o.order_line:
                raise UserError(_('You cannot submit a quotation/sales order which has no line.'))
        return self.write({'state': 'submitted'})

    # --added deep
    @api.multi
    def action_approve1(self):
        orders = self.filtered(lambda s: s.state in ['submitted'])
        orders.write({'state':'approved1'})
        return True

    @api.multi
    def action_approve2(self):
        orders = self.filtered(lambda s: s.state in ['approved1', 'submitted'])
        orders.write({'state': 'approved2',
                      'traffic_appr_date': fields.Date.context_today(self)})
        return True

    @api.multi
    def action_confirm(self):
        for order in self.filtered("advertising"):
            order.order_line.deadline_check()
            order.order_line.page_qty_check()
        super(SaleOrder, self).action_confirm()
        return True

    # --added deep
    @api.multi
    def action_refuse(self):
        orders = self.filtered(lambda s: s.state in ['submitted', 'sale', 'sent', 'approved1', 'approved2'])
        orders.write({'state':'draft'})
        return True

    # overridden: -- added deep
    @api.multi
    def print_quotation(self):
        self.filtered(lambda s: s.state == 'approved2').write({'state': 'sent'})
        return self.env['report'].get_action(self, 'sale.report_saleorder')


    '''@api.multi
    def write(self, vals):
        res = super(SaleOrder, self).write(vals)
        if self.advertising:
            if 'partner_id' in vals or 'nett_nett' in vals:
                self.update_line_discount()
        return res

    @api.model
    def create(self, vals):
        res = super(SaleOrder, self).create(vals)
        if self.advertising:
            res.update_line_discount()
        return res'''


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.depends('product_uom_qty', 'order_id.partner_id', 'comb_list_price', 'subtotal_before_agency_disc', 'discount', 'price_unit', 'tax_id')
    @api.multi
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
#        import pdb; pdb.set_trace()
        super(SaleOrderLine, self.filtered(lambda record: record.advertising != True))._compute_amount()
        for line in self.filtered('advertising'):
            comp_discount = line.computed_discount or 0.0
            price_unit = line.price_unit or 0.0
            unit_price = line.actual_unit_price or 0.0
            qty = line.product_uom_qty or 0.0
            csa = line.color_surcharge_amount or 0.0
            subtotal_bad = line.subtotal_before_agency_disc
            if line.order_id.partner_id.agency_discount and not line.order_id.nett_nett:
                discount = line.order_id.partner_id.agency_discount
            else:
                discount = 0.0

            if not line.multi_line:
                if price_unit == 0.0:
                    unit_price = 0.0
                    comp_discount = 0.0
                    subtotal_bad = 0.0
                    csa = 0.0
                elif price_unit > 0.0 and subtotal_bad > 0.0:
                    unit_price = round(float(subtotal_bad) / float(qty), 2)
                    comp_discount = round((float(price_unit + float(csa) - float(unit_price))) / (float(price_unit) + float(csa)) * 100.0, 2)
                elif price_unit > 0.0 and subtotal_bad == 0.0:
                    unit_price = 0.0
                    csa = 0.0
                    comp_discount = 100.0

                price = unit_price * (1 - (discount or 0) / 100.0)
                taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty, product=line.product_id,
                                                partner=line.order_id.partner_id)
                line.update({
                    'actual_unit_price': unit_price,
                    'price_tax': taxes['total_included'] - taxes['total_excluded'],
                    'price_total': taxes['total_included'],
                    'price_subtotal': taxes['total_excluded'],
                    'subtotal_before_agency_disc': subtotal_bad,
                    'color_surcharge_amount': csa,
                    'discount': discount,
                    'computed_discount': comp_discount,
                })
            else:
                clp = line.comb_list_price or 0.0
                if clp > 0.0:
                    comp_discount = round((float(clp) + float(csa) - float(subtotal_bad)) / (float(clp) + float(csa)) * 100.0,2)
                    unit_price = 0.0
                    price_unit = 0.0
                else:
                    subtotal_bad = 0.0
                    comp_discount = 0.0
                    csa = 0.0
                    unit_price = 0.0
                    price_unit = 0.0

                price = subtotal_bad * (1 - (discount or 0) / 100.0)
                taxes = line.tax_id.compute_all(price, line.order_id.currency_id, quantity=1,
                                                product=line.product_template_id, partner=line.order_id.partner_id)
                line.update({
                    'price_tax': taxes['total_included'] - taxes['total_excluded'],
                    'price_total': taxes['total_included'],
                    'price_subtotal': taxes['total_excluded'],
                    'actual_unit_price': unit_price,
                    'computed_discount': comp_discount,
                    'color_surcharge_amount': csa,
                    'price_unit': price_unit,
                    'discount': discount,
                })
        return True


    @api.depends('issue_product_ids.price')
    @api.multi
    def _multi_price(self):
        """
        Compute the combined price in the multi_line.
        """
        for order_line in self.filtered('advertising'):
            if order_line.issue_product_ids:
                price_tot = 0.0
                count = 0
                for ipi in order_line.issue_product_ids:
                    price_tot += ipi.price
                    count += 1
                order_line.update({
                    'comb_list_price': price_tot,
                    'multi_line_number': count,
                })

    @api.depends('adv_issue', 'ad_class')
    @api.multi
    def _compute_deadline(self):
        """
        Compute the deadline for this placement.
        """
        for line in self.filtered('advertising'):
            if line.ad_class:
                dt_offset = timedelta(hours=line.ad_class.deadline_offset or 0)
                line.deadline_offset = fields.Datetime.to_string(datetime.now() + dt_offset)
                if line.adv_issue and line.adv_issue.deadline:
                    dt_deadline = fields.Datetime.from_string(line.adv_issue.deadline)
                    line.deadline = fields.Datetime.to_string(dt_deadline - dt_offset)




    @api.depends('ad_class')
    @api.multi
    def _compute_tags_domain(self):
        """
        Compute the domain for the Pageclass domain.
        """
        for rec in self:
            rec.page_class_domain = json.dumps(
                [('id', 'in', rec.ad_class.tag_ids.ids)]
            )

    layout_remark = fields.Text('Layout Remark')
    title = fields.Many2one('sale.advertising.issue', 'Title', domain=[('child_ids','<>', False)])
    page_class_domain = fields.Char(compute=_compute_tags_domain, readonly=True, store=False,)
    title_ids = fields.Many2many('sale.advertising.issue', 'sale_order_line_adv_issue_title_rel', 'order_line_id', 'adv_issue_id', 'Titles')
    adv_issue_ids = fields.Many2many('sale.advertising.issue','sale_order_line_adv_issue_rel', 'order_line_id', 'adv_issue_id',  'Advertising Issues')
    issue_product_ids = fields.One2many('sale.order.line.issues.products', 'order_line_id', 'Adv. Issues with Product Prices')
    dates = fields.One2many('sale.order.line.date', 'order_line_id', 'Advertising Dates')
    dateperiods = fields.One2many('sale.order.line.dateperiod', 'order_line_id', 'Advertising Date Periods')
    date_type = fields.Selection(related='ad_class.date_type', type='selection',
                   selection=[
                        ('validity', 'Validity Date Range'),
                        ('date', 'Date of Publication'),
                        ('newsletter', 'Newsletter'),
                        ('online', 'Online'),
                        ('issue_date', 'Issue Date'),
                   ], relation='product.category', string='Date Type', readonly=True)
    adv_issue = fields.Many2one('sale.advertising.issue','Advertising Issue')
    issue_date = fields.Date(related='adv_issue.issue_date', string='Issue Date', store=True)
    medium = fields.Many2one('product.category', string='Medium')
    ad_class = fields.Many2one('product.category', 'Advertising Class')
    deadline = fields.Datetime(compute=_compute_deadline, string='Deadline', store=True)
    deadline_offset = fields.Datetime(compute=_compute_deadline)
    product_template_id = fields.Many2one('product.template', string='Product', domain=[('sale_ok', '=', True)],
                                 change_default=True, ondelete='restrict')
    page_reference = fields.Char('Reference of the Page', size=32)
    ad_number = fields.Char('Advertising Reference', size=32)
    url_to_material = fields.Char('Advertising Material', size=64)
    from_date = fields.Date('Start of Validity')
    to_date = fields.Date('End of Validity')
    state = fields.Selection([
        ('draft', 'Quotation'),
        ('submitted', 'Submitted for Approval'),
        ('approved1', 'Approved by Sales Mgr'),
        ('approved2', 'Approved by Traffic'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sale Order'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], related='order_id.state', string='Order Status', readonly=True, copy=False, store=True, default='draft')
    multi_line_number = fields.Integer(compute='_multi_price', string='Number of Lines', store=True)
    partner_acc_mgr = fields.Many2one(related='order_id.partner_acc_mgr', store=True, string='Account Manager', readonly=True)
    order_partner_id = fields.Many2one(related='order_id.partner_id', relation='res.partner', string='Customer')
    discount_dummy = fields.Float(related='discount', string='Agency Commission (%)', readonly=True )
    actual_unit_price = fields.Monetary(string='Actual Unit Price', required=True, default=0.0,
                                     digits=dp.get_precision('Actual Unit Price'), states={'draft': [('readonly', False)]})
    comb_list_price = fields.Monetary(compute='_multi_price', string='Combined_List Price', default=0.0, store=True,
                                digits=dp.get_precision('Actual Unit Price'))
    price_subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal', readonly=True)
    computed_discount = fields.Float(string='Discount (%)', digits=dp.get_precision('Account'), default=0.0)
    subtotal_before_agency_disc = fields.Monetary(string='Subtotal before Commission', digits=dp.get_precision('Account'))
    advertising = fields.Boolean(related='order_id.advertising', string='Advertising', store=True)
    multi_line = fields.Boolean(string='Multi Line')
    color_surcharge = fields.Boolean(string='Color Surcharge')
    color_surcharge_amount = fields.Monetary(string='Color Surcharge', digits=dp.get_precision('Account'), readonly=True)
    discount_reason_id = fields.Many2one('discount.reason', 'Discount Reason')

    @api.onchange('medium')
    def onchange_medium(self):
        vals, data, result = {}, {}, {}
        if not self.advertising:
            return {'value': vals }
        if self.medium:
            child_id = [x.id for x in self.medium.child_id]
            if len(child_id) == 1:
                vals['ad_class'] = child_id[0]
            else:
                vals['ad_class'] = False
                data = {'ad_class': [('id', 'child_of', self.medium.id), ('type', '!=', 'view')]}
            titles = self.env['sale.advertising.issue'].search([('parent_id','=', False),('medium', '=', self.medium.id)]).ids
            if titles and len(titles) == 1:
                vals['title'] = titles[0]
                vals['title_ids'] = [(6, 0, [])]
            else:
                vals['title'] = False
                vals['title_ids'] = [(6, 0, [])]
        return {'value': vals, 'domain': data }

    @api.onchange('ad_class')
    def onchange_ad_class(self):
        vals, data, result = {}, {}, {}
        if not self.advertising:
            return {'value': vals}
        if self.ad_class:
            product_ids = self.env['product.template'].search([('categ_id', '=', self.ad_class.id)])
            if product_ids:
                data['product_template_id'] = [('categ_id', '=', self.ad_class.id)]
                if len(product_ids) == 1:
                    vals['product_template_id'] = product_ids[0]
                else:
                    vals['product_template_id'] = False
            date_type = self.ad_class.date_type
            if date_type:
                vals['date_type'] = date_type
            else: result = {'title':_('Warning'),
                                 'message':_('The Ad Class has no Date Type. You have to define one')}
        else:
            vals['product_template_id'] = False
            vals['date_type'] = False
        return {'value': vals, 'domain' : data, 'warning': result}

    @api.onchange('title')
    def title_oc(self):
        data, vals = {}, {}
        if not self.advertising:
            return {'value': vals}
        if self.title:
            adissue_ids = self.title.child_ids.ids
            if len(adissue_ids) == 1:
                vals['adv_issue'] = adissue_ids[0]
                vals['adv_issue_ids'] = [(6, 0, [])]
                vals['product_id'] = False
                data.update({'adv_issue': [('id', 'in', adissue_ids)]})
            else:
                vals['adv_issue'] = False
                vals['product_id'] = False
                data.update({'adv_issue_ids': [('id', 'in', adissue_ids)]})
        return {'value': vals, 'domain': data}

    @api.onchange('title_ids')
    def title_ids_oc(self):
        vals = {}
        if not self.advertising:
            return {'value': vals}
        if self.title_ids and self.adv_issue_ids:
            titles = self.title_ids.ids
            issue_ids = self.adv_issue_ids.ids
            adv_issues = self.env['sale.advertising.issue'].search([('id', 'in', issue_ids)])
            issue_parent_ids = [x.parent_id.id for x in adv_issues]
            for title in titles:
                if not (title in issue_parent_ids):
                    raise UserError(_('Not for every selected Title an Issue is selected.'))
            if len(self.title_ids) == 1:
                self.title = self.title_ids[0]
                self.title_ids = [(6, 0, [])]

        elif self.title_ids and self.issue_product_ids:
            titles = self.title_ids.ids
            adv_issues = self.env['sale.advertising.issue'].search([('id', 'in', [x.adv_issue_id.id for x in self.issue_product_ids])])
            issue_parent_ids = [x.parent_id.id for x in adv_issues]
            back = False
            for title in titles:
                if not (title in issue_parent_ids):
                    back = True
            if back:
                self.adv_issue_ids = [(6, 0, adv_issues.ids)]
                self.issue_product_ids = [(6, 0, [])]
            if len(self.title_ids) == 1:
                self.title = self.title_ids[0]
                self.title_ids = [(6, 0, [])]
            self.titles_issues_products_price()

        elif self.title_ids and not self.issue_product_ids and not self.adv_issue_ids:
            self.product_template_id = False
            self.product_id = False

        else:
            self.adv_issue = False
            self.adv_issue_ids = [(6, 0, [])]
            self.issue_product_ids = [(6, 0, [])]
            self.product_id = False
            self.product_template_id = False
            self.product_uom = False



    @api.onchange('product_template_id')
    def titles_issues_products_price(self):
        vals = {}
        if not self.advertising:
            return {'value': vals}
        if self.product_template_id and self.adv_issue_ids and len(self.adv_issue_ids) > 1:
            self.product_uom = self.product_template_id.uom_id
            adv_issues = self.env['sale.advertising.issue'].search([('id', 'in', self.adv_issue_ids.ids)])
            values = []
            product_id = False
            price = 0
            issues_count = 0
            for adv_issue in adv_issues:
                if adv_issue.parent_id.id in self.title_ids.ids or adv_issue.parent_id.id == self.title:
                    value = {}
                    if adv_issue.product_attribute_value_id:
                        pav = adv_issue.product_attribute_value_id.id
                    else:
                        pav = adv_issue.parent_id.product_attribute_value_id.id
                    product_id = self.env['product.product'].search(
                        [('product_tmpl_id', '=', self.product_template_id.id), ('attribute_value_ids', '=', pav)])
                    if product_id:
                        product = product_id.with_context(
                            lang=self.order_id.partner_id.lang,
                            partner=self.order_id.partner_id.id,
                            quantity=self.product_uom_qty or 0,
                            date=self.order_id.date_order,
                            pricelist=self.order_id.pricelist_id.id,
                            uom=self.product_uom.id
                        )
                        if self.order_id.pricelist_id and self.order_id.partner_id:
                            value['product_id'] = product_id.id
                            value['adv_issue_id'] = adv_issue.id
                            value['price_unit'] = self.env['account.tax']._fix_tax_included_price_company(
                                self._get_display_price(product), product.taxes_id, self.tax_id,
                                self.company_id)

                            price += value['price_unit'] * self.product_uom_qty
                            values.append(value)
                issues_count += 1
            if product_id:
                self.update({
                    'adv_issue_ids': [(6, 0, [])],
                    'issue_product_ids': values,
                    'product_id': product_id.id,
                    'multi_line_number': issues_count,
                    'multi_line': True,
                })
            self.comb_list_price = price
            self.subtotal_before_agency_disc = price
        elif self.product_template_id and self.issue_product_ids and len(self.issue_product_ids) > 1:
            self.product_uom = self.product_template_id.uom_id
            adv_issues = self.env['sale.advertising.issue'].search([('id', 'in', [x.adv_issue_id.id for x in self.issue_product_ids])])
            values = []
            product_id = False
            price = 0
            issues_count = 0
            for adv_issue in adv_issues:
                if adv_issue.parent_id.id in self.title_ids.ids or adv_issue.parent_id.id == self.title.id:
                    value = {}
                    if adv_issue.product_attribute_value_id:
                        pav = adv_issue.product_attribute_value_id.id
                    else:
                        pav = adv_issue.parent_id.product_attribute_value_id.id
                    product_id = self.env['product.product'].search(
                        [('product_tmpl_id', '=', self.product_template_id.id), ('attribute_value_ids', '=', pav)])
                    if product_id:
                        if self.order_id.pricelist_id and self.order_id.partner_id:
                            value['product_id'] = product_id.id
                            value['adv_issue_id'] = adv_issue.id
                            value['price_unit'] = self.env['account.tax']._fix_tax_included_price_company(
                                self._get_display_price(product_id), product_id.taxes_id, self.tax_id,
                                self.company_id)

                            price += value['price_unit'] * self.product_uom_qty
                            values.append(value)
                issues_count += 1
            if product_id:
                self.update({
                    'issue_product_ids': values,
                    'product_id': product_id.id,
                    'multi_line_number': issues_count,
                    'multi_line': True,
                })
            self.comb_list_price = price
            self.subtotal_before_agency_disc = price
        elif self.product_template_id and (self.adv_issue or len(self.adv_issue_ids) == 1):
                if self.adv_issue_ids and len(self.adv_issue_ids) == 1:
                    self.adv_issue = self.adv_issue_ids.id
                if self.adv_issue.parent_id.id == self.title.id:
                    if self.adv_issue.product_attribute_value_id:
                        pav = self.adv_issue.product_attribute_value_id.id
                    else:
                        pav = self.adv_issue.parent_id.product_attribute_value_id.id
                    product_id = self.env['product.product'].search(
                        [('product_tmpl_id', '=', self.product_template_id.id), ('attribute_value_ids', '=', pav)])
                    if product_id:
                        self.update({
                            'adv_issue_ids': [(6, 0, [])],
                            'issue_product_ids': [(6, 0, [])],
                            'product_id': product_id.id,
                            'multi_line_number': 1,
                            'multi_line': False,
                        })

    @api.onchange('product_id')
    def product_id_change(self):
        result = super(SaleOrderLine, self).product_id_change()
        if not self.advertising:
            return result
        if not self.multi_line:
            self.subtotal_before_agency_disc = self.actual_unit_price = self.price_unit
        else:
            self.actual_unit_price = self.price_unit = 0.0
        self.product_uom_qty = 1
        return result

    @api.onchange('date_type')
    def onchange_date_type(self):
        vals = {}
        if not self.advertising:
            return {'value': vals}
        if self.date_type:
            if self.date_type == 'date':
                if self.dateperiods:
                    vals['dateperiods'] = [(6,0,[])]
                if self.adv_issue_ids:
                    vals['adv_issue_ids'] = [(6,0,[])]
            elif self.date_type == 'validity':
                if self.dates:
                    vals['dates'] = [(6,0,[])]
                if self.adv_issue_ids:
                    vals['adv_issue_ids'] = [(6,0,[])]
            elif self.date_type == 'issue_date':
                if self.dates:
                    vals['dates'] = [(6,0,[])]
                if self.dateperiods:
                    vals['dateperiods'] = [(6,0,[])]
        return {'value': vals}



    @api.onchange('actual_unit_price')
    def onchange_actualup(self):
        result = {}
        if not self.advertising:
            return {'value': result}
        if not self.multi_line:
            if self.actual_unit_price > 0.0:
                if self.price_unit > 0.0:
                    pcsa = float(self.price_unit) + float(self.color_surcharge_amount)
                    cdisc = round((pcsa - float(self.actual_unit_price)) / pcsa * 100.0,2)
                    result['computed_discount'] = cdisc
                    result['subtotal_before_agency_disc'] = round((float(self.actual_unit_price) * float(self.product_uom_qty)), 2)
                else:
                    result['actual_unit_price'] = 0.0
                    result['computed_discount'] = 0.0
                    result['subtotal_before_agency_disc'] = 0.0
            else:
                if self.price_unit > 0.0:
                    result['computed_discount'] = 100.0
                    result['subtotal_before_agency_disc'] = 0.0
        return {'value': result}

    @api.onchange('computed_discount')
    def onchange_actualcd(self):
        result = {}
        if not self.advertising:
            return {'value': result}
        if self.multi_line:
            clp = self.comb_list_price or 0.0
            csa = self.color_surcharge_amount or 0.0
            comp_discount = self.computed_discount
            if clp and clp > 0:
                subtotal_bad = round((float(clp) + float(csa) ) * float(1.0 - comp_discount / 100.0), 2)
                result['subtotal_before_agency_disc'] = subtotal_bad
            else:
                result['subtotal_before_agency_disc'] = 0.0
                result['computed_discount'] = 0.0
        return {'value': result}

#    @api.onchange('comb_list_price')
#    def onchange_actualclp(self):
#        result = {}
#        if not self.advertising:
#            return {'value': result}
#        if self.multi_line:
#            clp = self.comb_list_price or 0.0
#            comp_discount = self.computed_discount
#            if clp and clp > 0:
#                subtotal_bad = round(float(clp) * float(1.0 - comp_discount / 100.0), 2)
#                result['subtotal_before_agency_disc'] = subtotal_bad
#            else:
#                result['subtotal_before_agency_disc'] = 0.0
#                result['computed_discount'] = 0.0
#        return {'value': result}

    @api.onchange('product_uom_qty')
    def onchange_actualqty(self):
        result = {}
        if not self.advertising:
            return {'value': result}
        if not self.multi_line:
            self.subtotal_before_agency_disc = round((float(self.actual_unit_price) * float(self.product_uom_qty)), 2)

    @api.onchange('color_surcharge')
    def onchange_color(self):
        result = {}
        if not self.advertising:
            return {'value': result}
        pu = self.price_unit
        clp = self.comb_list_price
        if not self.multi_line:
            if self.color_surcharge:
                self.color_surcharge_amount = pu / 2
                aup = pu * 1.50
                self.computed_discount = 0.0
                self.actual_unit_price = aup
                self.subtotal_before_agency_disc = round((float(aup) * float(self.product_uom_qty)), 2)
            else:
                self.color_surcharge_amount = 0.0
                self.computed_discount = 0.0
                self.actual_unit_price = aup = pu
                self.subtotal_before_agency_disc = round((float(aup) * float(self.product_uom_qty)), 2)
        else:
            if self.color_surcharge:
                self.computed_discount = 0.0
                self.color_surcharge_amount = clp / 2
                self.subtotal_before_agency_disc = round((float(clp) * 1.50 ), 2)
            else:
                self.computed_discount = 0.0
                self.color_surcharge_amount = 0.0
                self.subtotal_before_agency_disc = clp


    @api.onchange('adv_issue', 'adv_issue_ids','dates','issue_product_ids')
    def onchange_getQty(self):
        result = {}
        if not self.advertising:
            return {'value': result}
        ml_qty = 0
        ai = self.adv_issue
        ais = self.adv_issue_ids
        ds = self.dates
        iis = self.issue_product_ids
        if ais:
            if len(ais) > 1:
                ml_qty = len(ais)
                ai = False
            else:
                ai = ais.id
                ais = [(6,0,[])]
                ml_qty = 1
        elif ai:
            ml_qty = 1
        elif ds:
            if len(ds) >= 1:
                ml_qty = 1
                self.product_uom_qty = len(ds)
        elif iis:
            if len(iis) > 1:
                ml_qty = len(iis)
        if ml_qty > 1:
            self.multi_line = True
        else:
            self.multi_line = False
            if not self.title and self.title_ids:
                self.title = self.title_ids[0]
            elif self.title:
                self.title_ids = [(6,0,[])]
        self.multi_line_number = ml_qty
        self.adv_issue = ai
        self.adv_issue_ids = ais



    @api.multi
    def _prepare_invoice_line(self, qty):
        res = super(SaleOrderLine, self)._prepare_invoice_line(qty)
        if self.advertising:
            res['account_analytic_id'] = self.adv_issue.analytic_account_id.id
        return res

#    @api.multi
#    def create(self, values):
#        if ('product_uom_qty' or 'adv_issue' or 'product_id') in values:
#            self.page_qty_check()
#        result = super(SaleOrderLine, self).create(values)
#        return result

    @api.multi
    def write(self, values):
        for line in self.filtered(lambda l: l.state == 'sale' and l.advertising):
            if ('adv_issue' or 'ad_class') in values:
                self.deadline_check()
                if ('product_uom_qty' or 'product_id') in values:
                    self.page_qty_check()
        result = super(SaleOrderLine, self).write(values)
        return result

    @api.multi
    def deadline_check(self):
        for line in self.filtered('advertising'):
            if line.deadline:
                if fields.Datetime.from_string(line.deadline) < datetime.now():
                    raise UserError(_('The deadline %s for this Category/Advertising Issue has passed.') %(line.deadline))
            elif line.issue_date and fields.Datetime.from_string(line.issue_date) < datetime.now():
                raise UserError(_('The Issue Date %s for this Advertising Issue has passed.') % (line.issue_date))


    @api.multi
    def page_qty_check(self):
        for line in self.filtered('advertising'):
            if not line.product_template_id.page_id:
                return
            lspace = line.product_uom_qty * line.product_template_id.space
            lpage = line.product_template_id.page_id.id
            if lspace > line.adv_issue.calc_page_space(lpage):
                raise UserError(_('There is not enough availability for this placement on %s in %s.') % (lpage, line.adv_issue))
            else:
                vals = {
                    'adv_issue_id': line.adv_issue.id,
                    'name': 'Afboeking',
                    'order_line_id': line.id,
                    'page_id': lpage,
                    'available_qty': - int(lspace)
                }
                self.env['sale.advertising.available'].create(vals)


class OrderLineAdvIssuesProducts(models.Model):

    _name = "sale.order.line.issues.products"
    _description= "Advertising Order Line Advertising Issues"
    _order = "order_line_id,sequence,id"


    @api.depends('price_unit', 'qty')
    def _compute_price(self):
        for line in self:
            line.price = line.price_unit * line.qty


    sequence = fields.Integer('Sequence', help="Gives the sequence of this line .", default=10)
    order_line_id = fields.Many2one('sale.order.line', 'Line', ondelete='cascade', index=True, required=True)
    adv_issue_id = fields.Many2one('sale.advertising.issue', 'Issue', ondelete='cascade', index=True, readonly=True, required=True)
    product_attribute_value_id = fields.Many2one(related='adv_issue_id.parent_id.product_attribute_value_id', relation='sale.advertising.issue',
                                      string='Title', readonly=True)
    product_id = fields.Many2one('product.product', 'Product', ondelete='cascade', index=True, readonly=True)
    price_unit = fields.Float('Unit Price', required=True, digits=dp.get_precision('Product Price'), default=0.0, readonly=True)
    qty = fields.Float(related='order_line_id.product_uom_qty', readonly=True)
    price = fields.Float(compute='_compute_price', string='Price', readonly=True, required=True, digits=dp.get_precision('Product Price'), default=0.0)
    page_reference = fields.Char('Reference of the Page', size=32)
    ad_number = fields.Char('Advertising Reference', size=32)
    url_to_material = fields.Char('Advertising Material', size=64)


class OrderLineDate(models.Model):

    _name = "sale.order.line.date"
    _description= "Advertising Order Line Dates"
    _order = "order_line_id,sequence,id"

    sequence = fields.Integer('Sequence', help="Gives the sequence of this line .", default=10)
    order_line_id = fields.Many2one('sale.order.line', 'Line', ondelete='cascade', index=True, required=True)
    issue_date = fields.Date('Date of Issue')
    name = fields.Char('Name', size=64)
    page_reference = fields.Char('Reference of the Page', size=32)
    ad_number = fields.Char('Advertising Reference', size=32)


class OrderLineDateperiod(models.Model):

    _name = "sale.order.line.dateperiod"
    _description= "Advertising Order Line Date Periods"
    _order = "order_line_id,sequence,id"

    sequence = fields.Integer('Sequence', help="Gives the sequence of this line .", default=10)
    order_line_id = fields.Many2one('sale.order.line', 'Line', ondelete='cascade', index=True, required=True)
    from_date = fields.Date('Start of Validity')
    to_date = fields.Date('End of Validity')
    name = fields.Char('Name', size=64)
    page_reference = fields.Char('Reference of the Page', size=32)
    ad_number = fields.Char('Advertising Reference', size=32)


class AdvertisingProof(models.Model):
    _name = "sale.advertising.proof"
    _description="Sale Advertising Proof"

    name = fields.Char('Name', size=32, required=True)
    address_id = fields.Many2one('res.partner','Delivery Address', required=True)
    number = fields.Integer('Number of Copies', required=True, default=1)
    target_id = fields.Many2one('sale.order','Target', required=True)

class DiscountReason(models.Model):
    _name = "discount.reason"
    _description="Discount Reason"
    
    name = fields.Char('Name', size=64, required=True)



class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    @api.multi
    def send_mail(self, auto_commit=False):
        if self._context.get('default_model') == 'sale.order' and self._context.get('default_res_id') and self._context.get('mark_so_as_sent'):
            order = self.env['sale.order'].browse([self._context['default_res_id']])
            if order.state == 'approved2':
                order.state = 'sent'
        return super(MailComposeMessage, self.with_context(mail_post_autofollow=True)).send_mail(auto_commit=auto_commit)



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

