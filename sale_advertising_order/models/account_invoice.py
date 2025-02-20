# Copyright 2017 Willem hulshof - <w.hulshof@magnus.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class Invoice(models.Model):
    _inherit = "account.move"

    ad = fields.Boolean(
        related="invoice_line_ids.ad",
        string="Ad",
        help="It indicates that the invoice is an Advertising Invoice.",
        store=True,
    )
    published_customer = fields.Many2one(
        "res.partner", "Advertiser", domain=[("is_customer", "=", True)]
    )
    invoice_description = fields.Text("Description")
    customer_contact = fields.Many2one(
        "res.partner", "Contact Person", domain=[("is_customer", "=", True)]
    )

    # Overridden:
    sale_type_id = fields.Many2one(
        comodel_name="sale.order.type",
        string="Sale Type",
        compute="_compute_sale_type_id",
        store=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
        ondelete="restrict",
        copy=True,
        precompute=True,
    )

    @api.depends("company_id")
    @api.depends_context("default_move_type", "active_model", "company")
    def _compute_sale_type_id(self):
        # If create invoice from sale order, sale type will not computed.
        if not self.env.context.get("default_move_type", False) or self.env.context.get(
            "active_model", False
        ) in ["sale.order", "sale.advance.payment.inv"]:
            return
        sale_type = self.env["sale.order.type"].browse()
        # self.sale_type_id = sale_type

        AdsSOT = self.env.ref("sale_advertising_order.ads_sale_type").id
        defSOT = self._context.get("default_move_type", False)

        for record in self:
            # Enforce
            if record.ad or (defSOT == AdsSOT):
                record.sale_type_id = AdsSOT
                continue

            elif record.sale_type_id:
                record.sale_type_id = record.sale_type_id
                continue

            if record.move_type not in ["out_invoice", "out_refund"]:
                record.sale_type_id = sale_type
                continue
            else:
                record.sale_type_id = record._origin.sale_type_id

            if not record.partner_id:
                record.sale_type_id = self.env["sale.order.type"].search(
                    [("company_id", "in", [self.env.company.id, False])], limit=1
                )
            else:
                sale_type = (
                    record.partner_id.with_company(record.company_id).sale_type
                    or record.partner_id.commercial_partner_id.with_company(
                        record.company_id
                    ).sale_type
                )
                if sale_type:
                    record.sale_type_id = sale_type

    def _get_name_invoice_report(self):
        self.ensure_one()
        ref = self.env.ref

        if self.sale_type_id.id == ref("sale_advertising_order.ads_sale_type").id:
            return "sale_advertising_order.report_invoice_document_sao"
        return super()._get_name_invoice_report()


class InvoiceLine(models.Model):
    _inherit = "account.move.line"

    @api.depends("price_unit", "quantity")
    def _compute_price(self):
        """
        Compute subtotal_before_agency_disc.
        """
        for line in self:
            sbad = 0.0
            if line.ad:
                price_unit = line.price_unit or 0.0
                qty = line.quantity or 0.0
                if price_unit and qty:
                    sbad = price_unit * qty

            line.subtotal_before_agency_disc = sbad

    so_line_id = fields.Many2one(
        "sale.order.line", "link between Sale Order Line and Invoice Line"
    )
    computed_discount = fields.Float(string="Discount")  # FIXME: seems not needed
    subtotal_before_agency_disc = fields.Float(
        compute="_compute_price", string="SBAD", readonly=True
    )
    ad_number = fields.Char(string="External Reference", size=50)
    sale_order_id = fields.Many2one(
        related="so_line_id.order_id", store=True, string="Order Nr."
    )
    ad = fields.Boolean(
        related="so_line_id.advertising",
        string="Ad",
        store=True,
        help="It indicates that the invoice line is from an Advertising Invoice.",
    )

    # Report: retain initial
    from_date = fields.Date("Start of Validity")
    to_date = fields.Date("End of Validity")
    issue_date = fields.Date()

    def open_sale_order(self):
        view_id = (
            self.env.ref("sale_advertising_order.sale_order_view_form_sao").id
            if self.sale_order_id.advertising
            else self.env.ref("sale.view_order_form").id
        )
        return {
            "type": "ir.actions.act_window",
            "name": "Sale Order",
            "view_mode": "form",
            "view_id": view_id,
            "res_model": "sale.order",
            "res_id": self.sale_order_id.id,
            "target": "current",
            "flags": {"initial_mode": "view"},
        }
