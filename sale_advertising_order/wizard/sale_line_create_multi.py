# -*- coding: utf-8 -*-
# Copyright 2017 Willem hulshof - <w.hulshof@magnus.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class sale_order_line_create_multi_lines(models.TransientModel):

    _name = "sale.order.line.create.multi.lines"
    _description = "Sale OrderLine Create Multi"
    
    def create_multi_lines(self, raise_exception=True):
        context = self._context
        model = context.get('active_model', False)
        n = 0
        all_lines = []
        if model and model == 'sale.order':
            order_ids = self.env['sale.order'].search([
                ('id','in', context.get('active_ids', []))])
            for so in order_ids:
                olines = so.order_line.filtered('multi_line')
                if not olines: continue
                for ol in olines:
                    all_lines.append(ol.id)
                    n += 1
            if n == 0:
                if raise_exception:
                    raise UserError(_(
                        'There are no Sales Order Lines with Multi Lines in '
                        'the selected Sales Orders.'
                    ))
            else:
                return self.create_multi_from_order_lines(orderlines=all_lines, orders=order_ids)

        elif model and model == 'sale.order.line':
            line_ids = context.get('active_ids', [])
            all_lines = self.env['sale.order.line'].search([
                ('id','in', line_ids),
                ('multi_line','=', True)
            ])
            if not all_lines:
                raise UserError(_('There are no Sales Order Lines with '
                                  'Multi Lines in the selection.'))
            orders = self.env['sale.order'].search([('id','in', all_lines.mapped('order_id'))])
            return self.create_multi_from_order_lines(orderlines=all_lines.ids, orders=orders)

    
    def create_multi_from_order_lines(self, orderlines=[], orders=None):
        return self.sudo().cmfol(orderlines=orderlines)

    
    def cmfol(self, orderlines=[]):
        sol_obj = self.env['sale.order.line']
        olines = sol_obj.browse(orderlines)
        lines = []
        for ol in olines:
            if ol.adv_issue_ids and not ol.issue_product_ids:
                raise UserError(_
                                ('The Order Line is in error. Please correct!'))
            elif ol.issue_product_ids:
                number_ids = len(ol.issue_product_ids)
                uom_qty = ol.multi_line_number / number_ids
                if uom_qty != 1:
                    raise UserError(_
                                    ('The number of Lines is different from the'
                                     ' number of Issues in the multi line.'))
                for ad_iss in ol.issue_product_ids:
                    res = self._prepare_default_vals_copy(ol, ad_iss)
                    vals = ol.copy_data(default=res)[0]
                    mol_rec = sol_obj.create(vals)
                    lines.append(mol_rec.id)
                ol.with_context(multi=True).unlink()
        return lines

    def _prepare_default_vals_copy(self, ol, ad_iss):
        ad_issue = self.env['sale.advertising.issue'].search([
                                ('id', '=', ad_iss.adv_issue_id.id)])

        sbad = (ad_iss.price_unit) * \
               ol.product_uom_qty * (1 - ol.computed_discount / 100.0)
        aup = sbad / ol.product_uom_qty
        res = {'title': ad_issue.parent_id.id,
                 'adv_issue': ad_issue.id,
                 'title_ids': [(6, 0, [ad_issue.parent_id.id])],
                 'adv_issue_ids': [(6, 0, [ad_issue.id])],
                 'product_id': ad_iss.product_id.id,
                 'price_unit': ad_iss.price_unit,
                 'issue_product_ids': False,
                 'subtotal_before_agency_disc': sbad,
                 'actual_unit_price': aup,
                 'order_id': ol.order_id.id or False,
                 'comb_list_price': 0.0,
                 'multi_line_number': 1,
                 'multi_line': False,
                 'ad_number': ad_iss.ad_number or ol.ad_number or False,
                 'page_reference': ad_iss.page_reference or
                                   ol.page_reference or False,
                 'url_to_material': ad_iss.url_to_material or
                                    ol.url_to_material or False,
                 'from_date': ol.date_type == 'issue_date' and ad_issue.issue_date or ol.from_date,
                 'to_date': ol.date_type == 'issue_date' and ad_issue.issue_date or ol.to_date,
         }

        return res



