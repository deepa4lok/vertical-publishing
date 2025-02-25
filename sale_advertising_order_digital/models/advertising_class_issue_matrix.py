from odoo import fields, models


class AdvertisingClassIssueMatrix(models.Model):
    _name = "advertising.class.issue.matrix"

    name = fields.Char(string="Advertising Class Issue Matrix", required=True)
