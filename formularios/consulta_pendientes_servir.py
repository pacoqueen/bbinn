#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
# Copyright (C) 2005-2008  Francisco José Rodríguez Bogado,                   #
#                          Diego Muñoz Escalante.                             #
# (pacoqueen@users.sourceforge.net, escalant3@users.sourceforge.net)          #
#                                                                             #
# This file is part of GeotexInn.                                             #
#                                                                             #
# GeotexInn is free software; you can redistribute it and/or modify           #
# it under the terms of the GNU General Public License as published by        #
# the Free Software Foundation; either version 2 of the License, or           #
# (at your option) any later version.                                         #
#                                                                             #
# GeotexInn is distributed in the hope that it will be useful,                #
# but WITHOUT ANY WARRANTY; without even the implied warranty of              #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the               #
# GNU General Public License for more details.                                #
#                                                                             #
# You should have received a copy of the GNU General Public License           #
# along with GeotexInn; if not, write to the Free Software                    #
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA  #
###############################################################################

###################################################################
## consulta_pendientes_servir.py - 
##      Pedidos y restos pendientes de servir
###################################################################
## NOTAS:
##  
###################################################################

from ventana import Ventana
import utils
import pygtk
pygtk.require('2.0')
import gtk, gtk.glade, time, sqlobject, os
try:
    import pclases
except ImportError:
    import sys
    from os.path import join as pathjoin
    sys.path.append(pathjoin("..", "framework"))
    import pclases
import mx, mx.DateTime
try:
    import geninformes
except ImportError:
    import sys
    sys.path.append(os.path.join('..','informes'))
    import geninformes
from utils import _float as float

def buscar_pendiente_servir(cliente = None, padre = None, wids = None):
    """
    Devuelve una tupla de 4 listas:
    pedidos pendientes de servir de fibra, total de fibra pendiente de servir 
    por producto, pedidos pendientes de servir de geotextiles, total de 
    geotextiles pendientes de servir por producto.
    Si "cliente" es distinto de None, busca sólo entre los pedidos del cliente.
    El parámetro "padre" se recibe para poder centrar la barra de progreso.
    """
    from ventana_progreso import VentanaProgreso
    vpro = VentanaProgreso(padre = padre)
    vpro.mostrar()
    if wids != None:
        wids['cbe_cliente'].pop_down()      # Por si se queda abierto el 
                        # combobox y no deja ver la ventana de progreso.
    while gtk.events_pending(): gtk.main_iteration(False)
    fibra_por_pedido = fibra_por_producto = None
    gtx_por_pedido = gtx_por_producto = None
    if pclases.ProductoVenta.select().count() > 0:
        vpro.set_valor(1/9.0, 
            "Analizando pedidos pendientes de servir (fibra)...")
        fibra = build_diccionario_pendiente_servir(cliente, "fibra")
        vpro.set_valor(2/9.0, 
            "Analizando pedidos pendientes de servir (geotextiles)...")
        gtx = build_diccionario_pendiente_servir(cliente, "geotextiles")
    vpro.set_valor(3/9.0, "Analizando pedidos pendientes de servir (otros)...")
    otros = build_diccionario_pendiente_servir(cliente, "otros")

    if pclases.ProductoVenta.select().count() > 0:
        vpro.set_valor(4/9.0, 
            "Analizando pedidos pendientes de servir (fibra)...")
        fibra_por_pedido, raw_fibra_por_producto=build_datos_por_pedido(fibra)
        vpro.set_valor(5/9.0, 
            "Analizando pedidos pendientes de servir (geotextiles)...")
        gtx_por_pedido, raw_gtx_por_producto = build_datos_por_pedido(gtx)
    vpro.set_valor(6/9.0, "Analizando pedidos pendientes de servir (otros)...")
    otros_por_pedido, raw_otros_por_producto = build_datos_por_pedido(otros)

    if pclases.ProductoVenta.select().count() > 0:
        vpro.set_valor(7/9.0, 
            "Analizando pedidos pendientes de servir (fibra)...")
        fibra_por_producto = build_datos_por_producto(raw_fibra_por_producto)
        vpro.set_valor(8/9.0, 
            "Analizando pedidos pendientes de servir (geotextiles)...")
        gtx_por_producto = build_datos_por_producto(raw_gtx_por_producto)
    vpro.set_valor(9/9.0, "Analizando pedidos pendientes de servir (otros)...")
    otros_por_producto = build_datos_por_producto(raw_otros_por_producto)
    vpro.ocultar()
    return (fibra_por_pedido, fibra_por_producto, 
            gtx_por_pedido, gtx_por_producto, 
            otros_por_pedido, otros_por_producto)

def build_datos_por_producto(por_producto):
    """
    Convierte el diccionario por producto en una lista de filas.
    """
    datos = []
    por_producto_sort = por_producto.keys()
    def cmp_por_nombre_producto(p1, p2):
        """
        Ordena una lista de productos por nombre de producto.
        (Es mentira, ordena por descripcón. Gñe)
        """
        if p1.descripcion < p2.descripcion:
            return -1
        if p1.descripcion > p2.descripcion:
            return 1
        return 0
    por_producto_sort.sort(cmp_por_nombre_producto)
    total_por_producto_pendiente = 0.0
    total_por_producto_existencias = 0.0
    total_por_producto_stock = 0.0
    total_por_producto_existencias_A = 0.0
    total_por_producto_stock_A = 0.0
    total_por_producto_existencias_B = 0.0
    total_por_producto_stock_B = 0.0
    for p in por_producto_sort:
        producto = p.descripcion
        str_stock = p.get_str_stock()
        kilos = p.get_stock()
        kilos_A = hasattr(p, "get_stock_A") and p.get_stock_A() or p.get_stock()
        kilos_B = hasattr(p, "get_stock_B") and p.get_stock_B() or 0.0
        bultos_A = hasattr(p, "get_existencias_A") and p.get_existencias_A() or p.get_existencias()
        bultos_B = hasattr(p, "get_existencias_B") and p.get_existencias_B() or 0.0
        pendiente = utils.float2str(por_producto[p])
        total_por_producto_pendiente += por_producto[p]
        id = p.id
        if not hasattr(p, "controlExistencias") or p.controlExistencias:
            if por_producto[p] > kilos_A:
                producto = "-> %s" % (producto)
                if por_producto[p] > kilos:
                    producto = '-' + producto
            existencias = str_stock
            bultos = p.get_str_existencias()
            total_por_producto_stock += p.get_existencias()
            total_por_producto_stock_A += bultos_A
            total_por_producto_stock_B += bultos_B
            total_por_producto_existencias += kilos
            total_por_producto_existencias_A += kilos_A
            total_por_producto_existencias_B += kilos_B
            datos.append((producto,
                          pendiente, 
                          existencias,
                          bultos,
                          kilos_A, 
                          bultos_A, 
                          kilos_B, 
                          bultos_B, 
                          id))
        else:
            datos.append((producto, 
                          pendiente, 
                          "-", "-", "-", "-", "-", "-",
                          id))
    datos.append((" >>> TOTAL: ", 
                  utils.float2str(total_por_producto_pendiente), 
                  utils.float2str(total_por_producto_existencias), 
                  utils.float2str(total_por_producto_stock, 0), 
                  utils.float2str(total_por_producto_existencias_A), 
                  utils.float2str(total_por_producto_stock_A, 0), 
                  utils.float2str(total_por_producto_existencias_B), 
                  utils.float2str(total_por_producto_stock_B, 0), 
                  0))
    return datos

def build_datos_por_pedido(fibra_o_gtx):
    """
    Devuelve una lista de filas con los datos por pedido y 
    un diccionario con los mismos datos pero por producto.
    """
    datos = []
    por_producto = {}
    LDPs_pendientes = fibra_o_gtx
    pedidos_keys_sorted = LDPs_pendientes.keys()
    def cmp_numpedido(p1, p2):
        """
        Comparación para ordenar por número de pedido.
        ¡CAMBIO! Ordena por fecha de pedido.
        """
        # De momento lo dejo aquí, "nested", porque no creo que me haga falta fuera y prefiero que tenga ámbito local.
        if p1.fecha < p2.fecha:
            return -1
        if p1.fecha > p2.fecha:
            return 1
        # Si misma fecha, por número de pedido:
        if p1.numpedido < p2.numpedido:
            return -1
        if p1.numpedido > p2.numpedido:
            return 1
        return 0
    pedidos_keys_sorted.sort(cmp_numpedido)
    for pedido in pedidos_keys_sorted:
        numpedido = pedido.numpedido
        fechapedido = pedido.fecha and pedido.fecha.strftime('%d/%m/%Y') or "-"
        cliente = pedido.cliente and pedido.cliente.nombre or "-"
        for producto in LDPs_pendientes[pedido]:
            for fechaentrega in LDPs_pendientes[pedido][producto]:
                for textoentrega in LDPs_pendientes[pedido][producto][fechaentrega]:
                    pendiente = LDPs_pendientes[pedido][producto][fechaentrega][textoentrega]
                    str_pendiente = utils.float2str(pendiente)
                    if producto not in por_producto:
                        por_producto[producto] = 0
                    por_producto[producto] += pendiente
                    str_producto = producto.descripcion
                    str_fechaentrega = utils.str_fecha(fechaentrega)
                    if not hasattr(producto, "controlExistencias") or producto.controlExistencias:
                        if (hasattr(producto, "get_stock_A") and pendiente > producto.get_stock_A()) \
                           or (not hasattr(producto, "get_stock_A") and pendiente > producto.get_stock()):
                            str_producto = "-> %s" % (str_producto)
                        if pendiente > producto.get_stock():
                            str_producto = "-" + str_producto
                    str_existencias = producto.get_str_stock()
                    id = pedido.id
                    if not hasattr(producto, "controlExistencias") or producto.controlExistencias:
                        datos.append((numpedido,
                                      fechapedido,
                                      cliente, 
                                      str_producto,
                                      str_pendiente, 
                                      str_existencias, 
                                      str_fechaentrega, 
                                      textoentrega or "", 
                                      id))
                    else:
                        datos.append((numpedido, 
                                      fechapedido, 
                                      cliente, 
                                      str_producto, 
                                      str_pendiente, 
                                      "-", 
                                      str_fechaentrega, 
                                      textoentrega or "", 
                                      id))
    return datos, por_producto


def build_diccionario_pendiente_servir(cliente, tipo):
    """
    Construye y devuelve un diccionario que será de la forma 
    LDPs_pendientes[pedido][producto][fecha_entrega][texto_entrega] = 
        cantidad_pendiente
    """
    LDPs_pendientes = {}    
    # Pedidos no cerrados.
    if cliente == None:
        pedidos = pclases.PedidoVenta.select(
            pclases.PedidoVenta.q.cerrado == False, orderBy = "numpedido")
    else:
        pedidos = pclases.PedidoVenta.select(pclases.AND(
                pclases.PedidoVenta.q.cerrado == False,
                pclases.PedidoVenta.q.clienteID == cliente.id), 
            orderBy = "numpedido")
    # Filtro todas las LDP y me quedo con las realmente pendientes del tipo 
    # especificado:
    for pedido in pedidos:
        if tipo == "geotextiles":
            ldps_pedido = [ldp for ldp in pedido.lineasDePedido 
                           if ldp.productoVenta 
                               and ldp.productoVenta.es_rollo()]
        elif tipo == "fibra":
            ldps_pedido = [ldp for ldp in pedido.lineasDePedido 
                           if ldp.productoVenta 
                               and (ldp.productoVenta.es_bala() 
                                    or ldp.productoVenta.es_bigbag())] 
        else:
            ldps_pedido = [ldp for ldp in pedido.lineasDePedido 
                           if (ldp.productoVenta 
                               and not ldp.productoVenta.es_bala()
                               and not ldp.productoVenta.es_rollo() 
                               and not ldp.productoVenta.es_bigbag())
                           or (ldp.productoCompra 
                               and not ldp.productoCompra.obsoleto)]
        for ldp in ldps_pedido:
            cantidad_servida = ldp.cantidadServidaPropia
            if cantidad_servida < ldp.cantidad:    # Aún queda por servir
                pedido = ldp.pedidoVenta
                producto = ldp.producto
                fechaentrega = ldp.fechaEntrega
                textoentrega = ldp.textoEntrega
                cantidad = ldp.cantidad - cantidad_servida
                if pedido not in LDPs_pendientes:
                    LDPs_pendientes[pedido] = {}
                if producto not in LDPs_pendientes[pedido]:
                    LDPs_pendientes[pedido][producto] = {}
                if fechaentrega not in LDPs_pendientes[pedido][producto]:
                    LDPs_pendientes[pedido][producto][fechaentrega] = {}
                if (textoentrega 
                    not in LDPs_pendientes[pedido][producto][fechaentrega]):
                    LDPs_pendientes[pedido][producto][fechaentrega][textoentrega] = 0
                LDPs_pendientes[pedido][producto][fechaentrega][textoentrega] += cantidad
    return LDPs_pendientes


class PendientesServir(Ventana):

    def __init__(self, objeto = None, usuario = None):
        """
        Constructor. objeto puede ser un objeto de pclases con el que
        comenzar la ventana (en lugar del primero de la tabla, que es
        el que se muestra por defecto).
        """
        self.usuario = usuario
        Ventana.__init__(self, 'consulta_pendientes_servir.glade', objeto)
        connections = {'b_salir/clicked': self.salir,
                       'b_imprimir/clicked': self.imprimir, 
                       'cbe_cliente/changed': self.cambiar_cliente} 
        self.add_connections(connections)
        self.inicializar_ventana()
        gtk.main()
    
    def cambiar_cliente(self, cb):
        self.rellenar_tabla()
    
    def rellenar_tabla(self):
        idcliente = utils.combo_get_value(self.wids['cbe_cliente'])
        if idcliente >= 0:
            if idcliente != 0:
                # Filtrar el cliente.
                self.fpped, self.fppro, self.gpped, self.gppro, self.opped, self.oppro = buscar_pendiente_servir(cliente = pclases.Cliente.get(idcliente), padre = self.wids['ventana'])
            else:
                # No filtrarlo
                self.fpped, self.fppro, self.gpped, self.gppro, self.opped, self.oppro = buscar_pendiente_servir(cliente = None, padre = self.wids['ventana'])
            tvs = []
            if pclases.ProductoVenta.select().count() > 0:
                tvs += [(self.fpped, 'tv_fibra_por_pedido'), 
                        (self.fppro, 'tv_fibra_por_producto'), 
                        (self.gpped, 'tv_gtx_por_pedido'), 
                        (self.gppro, 'tv_gtx_por_producto')]
            tvs += [(self.opped, 'tv_otros_por_pedido'), 
                    (self.oppro, 'tv_otros_por_producto')]
            for datos, tv in tvs:
                self.rellenar_tv(datos, tv)

    def rellenar_tv(self, datos, nombretv):
        model = self.wids[nombretv].get_model()
        model.clear()
        for fila in datos:
            model.append(fila)
    
    def abrir_pedido(self, tv, path, view_column):
        model = tv.get_model()
        idpedido = model[path][-1]
        if idpedido > 0:
            import pedidos_de_venta
            v = pedidos_de_venta.PedidosDeVenta(pclases.PedidoVenta.get(idpedido), usuario = self.usuario)

    def inicializar_ventana(self):
        """
        Inicializa los controles de la ventana, estableciendo sus
        valores por defecto, deshabilitando los innecesarios,
        rellenando los combos, formateando el TreeView -si lo hay-...
        """
        self.wids['ventana'].resize(800, 600)
        self.ffped = self.fppro = self.gpped = self.gppro = None
        cols = (('Pedido', 'gobject.TYPE_STRING', False, True, True, None), 
                ('Fecha', 'gobject.TYPE_STRING', False, True, False, None), 
                ('Cliente', 'gobject.TYPE_STRING', False, True, False, None), 
                ('Producto', 'gobject.TYPE_STRING', False, True, False, None), 
                ('Pendiente', 'gobject.TYPE_STRING', False, True, False, None), 
                ('Existencias totales', 'gobject.TYPE_STRING', False, True, False, None), 
                ('Fecha entrega', 'gobject.TYPE_STRING', False, True, False, None), 
                ('Texto entrega', 'gobject.TYPE_STRING', False, True, False, None), 
                ('IDPedido', 'gobject.TYPE_INT64', False, False, False, None))
        utils.preparar_listview(self.wids['tv_fibra_por_pedido'], cols)
        utils.preparar_listview(self.wids['tv_gtx_por_pedido'], cols)
        utils.preparar_listview(self.wids['tv_otros_por_pedido'], cols)
        self.wids['tv_fibra_por_pedido'].connect("row-activated", self.abrir_pedido)
        self.wids['tv_gtx_por_pedido'].connect("row-activated", self.abrir_pedido)
        self.wids['tv_otros_por_pedido'].connect("row-activated", self.abrir_pedido)
        cols = (('Producto', 'gobject.TYPE_STRING', False, True, True, None), 
                ('Pendiente', 'gobject.TYPE_STRING', False, True, False, None), 
                ('Existencias totales', 'gobject.TYPE_STRING', False, True, False, None), 
                ('Bultos totales', 'gobject.TYPE_STRING', False, True, False, None), 
                ('Existencias clase A', 'gobject.TYPE_STRING', False, True, False, None), 
                ('Bultos clase A', 'gobject.TYPE_STRING', False, True, False, None), 
                ('Existencias clase B', 'gobject.TYPE_STRING', False, True, False, None), 
                ('Bultos clase B', 'gobject.TYPE_STRING', False, True, False, None), 
                ('IDPedido', 'gobject.TYPE_INT64', False, False, False, None))
        utils.preparar_listview(self.wids['tv_fibra_por_producto'], cols)
        utils.preparar_listview(self.wids['tv_gtx_por_producto'], cols)
        utils.preparar_listview(self.wids['tv_otros_por_producto'], cols)
        self.colorear(self.wids['tv_fibra_por_producto'])
        self.colorear(self.wids['tv_gtx_por_producto'])
        self.colorear(self.wids['tv_otros_por_producto'])
        self.colorear(self.wids['tv_fibra_por_pedido'])
        self.colorear(self.wids['tv_gtx_por_pedido'])
        self.colorear(self.wids['tv_otros_por_pedido'])
        utils.rellenar_lista(self.wids['cbe_cliente'], [(0, "Todos los clientes")] + [(c.id, c.nombre) for c in pclases.Cliente.select(orderBy="nombre")])
        def iter_cliente_seleccionado(completion, model, iter):
            idcliente = model[iter][0]
            utils.combo_set_from_db(self.wids['cbe_cliente'], idcliente)
        self.wids['cbe_cliente'].child.get_completion().connect('match-selected', iter_cliente_seleccionado)
        self.wids['cbe_cliente'].grab_focus()
        if pclases.ProductoVenta.select().count() > 0:
            self.wids['notebook1'].set_current_page(1)
        else:
            self.wids['notebook1'].remove_page(1)
            self.wids['notebook1'].remove_page(0)
            self.wids['notebook1'].set_current_page(-1)
    
    def colorear(self, tv):
        """
        Colorea el listview dependiendo de si la cantidad pendiente de 
        servir es superior a las existencias en almacén.
        """
        def cell_func(column, cell, model, itr, numcol):
            """
            Si la fila corresponde a una factura cobrada en un pagaré, colorea la 
            fila completa con un color generado a partir del número de pagaré.
            """
            if "-->" in model[itr][0] or "-->" in model[itr][3]:
                cell.set_property("cell-background", "IndianRed3")
            elif "->" in model[itr][0] or "->" in model[itr][3]:
                cell.set_property("cell-background", "IndianRed1")
            else:
                cell.set_property("cell-background", None)
        cols = tv.get_columns()
        for i in xrange(len(cols)):
            column = cols[i]
            cells = column.get_cell_renderers()
            for cell in cells:
                column.set_cell_data_func(cell, cell_func, i)

    def imprimir(self, boton):
        """
        Imprime la información en dos documentos: fibra y geotextiles.
        """
        import informes
        idcliente = utils.combo_get_value(self.wids['cbe_cliente'])
        if idcliente > 0:
            nombrecliente = pclases.Cliente.get(idcliente).nombre
        else:
            nombrecliente = ""
        if self.gpped != None and self.gpped != []:
            informes.abrir_pdf(geninformes.pendiente_servir("geotextiles", self.gpped, self.gppro, nombrecliente))
        if self.fpped != None and self.fpped != []:
            informes.abrir_pdf(geninformes.pendiente_servir("fibra", self.fpped, self.fppro, nombrecliente))
        if self.opped != None and self.opped != []:
            informes.abrir_pdf(geninformes.pendiente_servir("otros", self.opped, self.oppro, nombrecliente))


if __name__ == '__main__':
    t = PendientesServir()


