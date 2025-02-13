from odoo.tests.common import TransactionCase


class CommonSaleAdvertisingOrder(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer = cls.env['res.partner'].search([('is_customer', '=', True)], limit=1)
        cls.one_issue_product = cls.env.ref('sale_advertising_order.product_template_digital1')
        cls.multi_issue_product = cls.env.ref('sale_advertising_order.product_template_digital2')
        cls.order = cls.env['sale.order'].create({
            'advertising': True,
            'published_customer': cls.customer.id,
            'partner_id': cls.customer.id,
            'type_id': cls.env.ref('sale_advertising_order.ads_sale_type').id,
        })
        cls.order_view = cls.env.ref("sale_advertising_order.sale_order_view_form_sao")
        cls.product_template_digital1 = cls.env.ref('sale_advertising_order.product_template_digital1')
        cls.product_template_digital2 = cls.env.ref('sale_advertising_order.product_template_digital2')
        cls.product_category_main = cls.env.ref('sale_advertising_order.digital_advertising_category')
        cls.product_category_sub = cls.env.ref('sale_advertising_order.product_category_ads_digital1')
        cls.title1 = cls.env.ref('sale_advertising_order.title1')
        cls.title2 = cls.env.ref('sale_advertising_order.title2')
        cls.issue1 = cls.env.ref('sale_advertising_order.issue1')
        cls.issue2 = cls.env.ref('sale_advertising_order.issue2')
        cls.issue3 = cls.env.ref('sale_advertising_order.issue3')
        cls.discount_reason = cls.env.ref('sale_advertising_order.discount_reason1')
