# -*- coding: utf-8 -*-
from openerp.osv import fields, orm
from openerp.tools.translate import _

class StockMove(orm.Model):
    _inherit = "stock.move"
    _columns = {
        'boxes': fields.integer('Boxes'),
        'packs': fields.integer('Packs'),
        'items': fields.integer('Items'),
        'bags' : fields.integer('Bags'),
        'pack_product_packaging': fields.many2one('product.packaging', 'Pack Packaging'),
    }

    def write(self, cr, uid, ids, vals, context=None):
        if 'product_qty' in vals and vals['product_qty'] > 0 or 'product_id' in vals and vals['product_id'] or 'bags' in vals:
            for move_id in ids:
                vals2 = vals.copy()
                if not 'bags' in vals:
                    vals2.update(self._packages_detail(cr, uid, vals, move_id, context))
                res = super(StockMove, self).write(cr, uid, [move_id], vals2, context)
                if vals.get('picking_id'):
                    picking_id = vals['picking_id']
                else:
                    picking_info = self.read(cr, uid, [move_id], ['picking_id'])[0]['picking_id']
                    if picking_info:
                        picking_id = picking_info[0]
                if picking_id:
                    picking_obj = self.pool['stock.picking']
                    bags = picking_obj._get_number_of_packages(cr, uid, [picking_id], context)[picking_id]
                    picking_obj.write(cr, uid, [picking_id], {'number_of_packages': bags})
        else:
            res = super(StockMove, self).write(cr, uid, ids, vals, context)
        return res

    def create(self, cr, uid, vals, context=None):
        if 'product_qty' in vals and vals['product_qty'] > 0 and 'product_id' in vals and vals['product_id']:
            vals.update(self._packages_detail(cr, uid, vals, False, context))
        return super(StockMove, self).create(cr, uid, vals, context)

    def onchange_quantity(self, cr, uid, ids, product_id, product_qty,
                          product_uom, product_uos):
        res = super(StockMove, self).onchange_quantity(cr, uid, ids, product_id, product_qty, product_uom, product_uos)
        if product_qty > 0 or product_id:
            vals = {'product_qty': product_qty, 'product_id': product_id}
            res['value'].update(self._packages_detail(cr, uid, vals, ids and ids[0]))
        return res

    def _packages_detail(self, cr, uid, vals, move_id=False, context=None):
        #TODO deal with product_qty = 0
        if vals.get('product_id'):
            product_id = vals['product_id']
        elif move_id:
            product_id = self.pool['stock.move'].read(cr, uid, [move_id], ['product_id'])[0]['product_id'][0]
        else:
            return {}
        if vals.get('product_qty') and vals['product_qty'] > 0:
            product_qty = vals['product_qty']
        elif move_id:
            product_qty = self.pool['stock.move'].read(cr, uid, [move_id], ['product_qty'])[0]['product_qty']
        else:
            return {}

        #Boxes:
        box_ul_ids = self.pool['product.ul'].search(cr, uid, [('type', '=', 'box')])
        package_obj = self.pool['product.packaging']
        box_package_ids = package_obj.search(cr, uid, [('product_id', '=', product_id), ('ul', 'in', box_ul_ids)])
        if box_package_ids:
            boxes_qty = package_obj.read(cr, uid, [box_package_ids[0]], ['qty'], context)[0]['qty']
            if boxes_qty > 0:
                boxes = int(product_qty / boxes_qty)
            else:
                boxes = 0
        else:
            boxes_qty = 0
            boxes = 0

        #Packs:
        pack_ul_id = self.pool['product.ul'].search(cr, uid, [('type', '=', 'pack')])
        pack_package_ids = package_obj.search(cr, uid, [('product_id', '=', product_id), ('ul', 'in', pack_ul_id)])
        if pack_package_ids:
            pack_qty = package_obj.read(cr, uid, [pack_package_ids[0]], ['qty'], context)[0]['qty']
            if pack_qty:
                packs = int((product_qty - boxes * boxes_qty) / pack_qty)
            else:
                packs = 0
        else:
            pack_qty = 0
            packs = 0

        #Items:
        items = product_qty - boxes * boxes_qty - packs * pack_qty

        #Bags:
        if items > 0:
            bags = boxes + packs + 1
        else:
            bags = boxes + packs

        res = {'boxes': boxes, 'packs': packs, 'items': items, 'bags': bags}
        if box_package_ids:
            res.update({'product_packaging': box_package_ids[0]})
        if pack_package_ids:
            res.update({'pack_product_packaging': pack_package_ids[0]})
        return res


class StockPicking(orm.Model):
    _inherit = "stock.picking"

    def _get_number_of_packages(self, cr, uid, ids, context=None):
        res = {}
        for picking in self.browse(cr, uid, ids, context=context):
            res[picking.id] = 0
            for move in picking.move_lines:
                res[picking.id] += move.bags
        return res


class StockPickingOut(orm.Model):
    _inherit = "stock.picking.out"

    def write(self, cr, uid, ids, vals, context=None):
        if 'move_lines' in vals:
            res = super(StockPickingOut, self).write(cr, uid, ids, vals, context)
            vals2 = self._get_number_of_packages(cr, uid, ids, context)
            for picking_id in ids:
                super(StockPickingOut, self).write(cr, uid, [picking_id], {'number_of_packages': vals2[picking_id]}, context)
        else:
            res = super(StockPickingOut, self).write(cr, uid, ids, vals, context)
        return res

    def _get_number_of_packages(self, cr, uid, ids, context=None):
        res = {}
        for picking in self.browse(cr, uid, ids, context=context):
            res[picking.id] = 0
            for move in picking.move_lines:
                res[picking.id] += move.bags
        return res


