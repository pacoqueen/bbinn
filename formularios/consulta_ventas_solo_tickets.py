#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
# Copyright (C) 2005-2008  Francisco José Rodríguez Bogado                    #
#                          (pacoqueen@users.sourceforge.net)                  #
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
## consulta_ventas_solo_tickets.py - sum((PVP - IVA) * porcentaje_tarifa)
###################################################################
## NOTAS:
##  - Solo cuenta lineas de venta, no servicios (que además no se 
##    pueden vender por TPV, ergo no tienen ticket).
##  - Las LDVs de tickets facturados se ignoran.
###################################################################
## Changelog:
## 
###################################################################
## Consulta tanto por ticket como agrupada por tipo de material (familia).
###################################################################
from ventana import Ventana
import utils
import pygtk
pygtk.require('2.0')
import gtk, gtk.glade, time, sqlobject
import sys, os
try:
    import pclases
except ImportError:
    sys.path.append(os.path.join('..', 'framework'))
    import pclases
import mx
try:
    import geninformes
except ImportError:
    sys.path.append(os.path.join('..', 'informes'))
    import geninformes
try:
    from treeview2pdf import treeview2pdf
except ImportError:
    sys.path.append(os.path.join("..", "informes"))
    from treeview2pdf import treeview2pdf
try:
    from treeview2csv import treeview2csv
except ImportError:
    sys.path.append(os.path.join("..", "informes"))
    from treeview2pdf import treeview2pdf
from informes import abrir_pdf, abrir_csv
import ventana_progreso

class ConsultaBeneficioSoloTickets(Ventana):
    def __init__(self, objeto = None, usuario = None):
        self.usuario = usuario
        Ventana.__init__(self, 'consulta_ventas_ticket.glade', objeto)
        connections = {'b_salir/clicked': self.salir,
                       'b_buscar/clicked': self.buscar,
                       'b_imprimir/clicked': self.imprimir,
                       'b_exportar/clicked': self.exportar,
                       'b_fecha_inicio/clicked': self.set_inicio,
                       'b_fecha_fin/clicked': self.set_fin}
        self.add_connections(connections)
        cols = (('Fecha', 'gobject.TYPE_STRING', False, True, False, None),
                ('Ticket', 'gobject.TYPE_STRING',False,True,True,None),
                ('Imp. total', 'gobject.TYPE_STRING',False,True,False,None),
                ('Imp. (s/IVA)','gobject.TYPE_STRING',False,True,False,None),
                ('Ben. sobre tarifa', 'gobject.TYPE_STRING', 
                    False, True, False, None),
                ('ID','gobject.TYPE_STRING', False, False, False, None))
        utils.preparar_treeview(self.wids['tv_datos'], cols)
        for col in self.wids['tv_datos'].get_columns()[2:]:
            for cell in col.get_cell_renderers():
                cell.set_property("xalign", 1.0)
            col.set_alignment(0.5)
        self.wids['tv_datos'].connect("row-activated", self.abrir_producto)
        self.fin = mx.DateTime.today()
        #self.inicio = mx.DateTime.DateTimeFrom(day = 1, month = self.fin.month, year = self.fin.year)
        self.inicio = self.fin
        self.wids['e_fechafin'].set_text(utils.str_fecha(self.fin))
        self.wids['e_fechainicio'].set_text(utils.str_fecha(self.inicio))
        self.wids['hbox1'].set_property("visible", False)
        self.wids['hbox6'].set_property("visible", False)
        gtk.main()

    def abrir_producto(self, tv, path, vc):                                     
        """
        Abre el producto al que se le ha hecho doble clic en una ventana nueva.
        """
        model = tv.get_model()
        tipo_e_id = model[path][-1]
        if "LDV" in tipo_e_id:
            tipo, id = tipo_e_id.split(':')
            ldv = pclases.LineaDeVenta.get(id)
            producto = ldv.producto
            if isinstance(producto, pclases.ProductoVenta):
                if producto.es_rollo():
                    import productos_de_venta_rollos
                    ventana_producto = productos_de_venta_rollos.ProductosDeVentaRollos(producto, usuario = self.usuario)
                elif producto.es_bala() or producto.es_bigbag():
                    import productos_de_venta_balas
                    ventana_producto = productos_de_venta_balas.ProductosDeVentaBalas(producto, usuario = self.usuario)
            elif isinstance(producto, pclases.ProductoCompra): 
                import productos_compra
                ventana_producto = productos_compra.ProductosCompra(producto, usuario = self.usuario)

    def chequear_cambios(self):
        pass

    def rellenar_tabla_por_ticket(self, resultados):
        """
        Rellena el model con los items de la consulta
        """        
        model = self.wids['tv_datos'].get_model()
        model.clear()
        totfact = totsiniva = totbeneficio = totbeneficio_cobro = 0.0
        self.wids['tv_datos'].freeze_child_notify()
        self.wids['tv_datos'].set_model(None)
        totcobrado = totpendiente = 0.0
        total_costo = total_costo_cobrado = 0.0
        tratados = {}
        for material in resultados:
            for fecha in resultados[material]:
                if fecha:
                    str_fecha = utils.str_fecha(fecha)
                else:
                    str_fecha = ""
                for ldv in resultados[material][fecha]:
                    # Para que coincidan los totales con la suma de las 
                    # columnas y por coherencia con todas las cifras de la 
                    # ventana, es necesario redondear a 2 decimales.
                    subtotal = round(ldv.get_subtotal(iva = True), 2)
                    subtotal_siva = round(ldv.get_subtotal(iva = False), 2)
                    beneficio = round(ldv.calcular_beneficio(), 2)
                    costo = round(ldv.calcular_precio_costo()*ldv.cantidad, 2)
                    fac_alb_tic = "Ticket %d" % ldv.ticket.numticket
                    cobrado = subtotal
                    pendiente = 0.0
                    beneficio_cobro = beneficio
                    costo_cobrado = costo
                        # Los tickets se asume que se cobran siempre, por 
                        # tanto el costo de los productos sobre lo cobrado 
                        # es del 100%.
                    desc_producto = utils.wrap(ldv.producto.descripcion, 40)
                    try:
                        beneficio_costo = 100.0 * beneficio / costo
                    except ZeroDivisionError:
                        beneficio_costo = 0.0
                    if ldv.ticket not in tratados:
                        padre_ticket = model.append(None, 
                            (str_fecha, 
                             ldv.ticket.numticket, 
                             "0", 
                             "0", 
                             "0", 
                             ""))
                        tratados[ldv.ticket] = padre_ticket
                    else:
                        padre_ticket = tratados[ldv.ticket]
                    model.append(padre_ticket, (desc_producto, 
                                                fac_alb_tic, 
                                                utils.float2str(subtotal), 
                                                utils.float2str(subtotal_siva), 
                                                "%s (%s%%)" % (
                                                   utils.float2str(beneficio), 
                                                   utils.float2str(
                                                       beneficio_costo)), 
                                                "LDV:%d" % ldv.id))
                    # Actualizo totales en memoria y en nodos padre TreeView
                    totfact += subtotal
                    totsiniva += subtotal_siva
                    totbeneficio += beneficio
                    totbeneficio_cobro += beneficio_cobro
                    totcobrado += cobrado
                    totpendiente += pendiente
                    total_costo += costo
                    total_costo_cobrado += costo_cobrado
                    model[padre_ticket][2] = utils.float2str(
                                            utils._float(model[padre_ticket][2]) 
                                                         + subtotal)
                    model[padre_ticket][3] = utils.float2str(
                                            utils._float(model[padre_ticket][3]) 
                                                         + subtotal_siva)
                    model[padre_ticket][4] = utils.float2str(
                                            utils._float(model[padre_ticket][4]) 
                                                         + beneficio)
        self.rellenar_totales(totfact, totsiniva, totbeneficio, 
                              totcobrado, totpendiente, totbeneficio_cobro, 
                              total_costo, total_costo_cobrado)
        self.wids['tv_datos'].set_model(model)
        self.wids['tv_datos'].thaw_child_notify()


    def rellenar_tabla(self, resultados):
        """
        Rellena el model con los items de la consulta
        """        
        model = self.wids['tv_datos'].get_model()
        model.clear()
        totfact = totsiniva = totbeneficio = totbeneficio_cobro = 0.0
        self.wids['tv_datos'].freeze_child_notify()
        self.wids['tv_datos'].set_model(None)
        totcobrado = totpendiente = 0.0
        total_costo = total_costo_cobrado = 0.0
        for material in resultados:
            if material != None:
                nombre_mat = material.descripcion
            else:
                nombre_mat = ""
            padre_mat = model.append(None, (nombre_mat, 
                                            "", 
                                            "0", 
                                            "0", 
                                            "0", 
                                            "M:%d" % (material 
                                                      and material.id
                                                      or -1)))
            for fecha in resultados[material]:
                if fecha:
                    str_fecha = utils.str_fecha(fecha)
                else:
                    str_fecha = ""
                padre_fec = model.append(padre_mat, (str_fecha, 
                                                     "", 
                                                     "0", 
                                                     "0", 
                                                     "0", 
                                                     ""))
                for ldv in resultados[material][fecha]:
                    # Para que coincidan los totales con la suma de las 
                    # columnas y por coherencia con todas las cifras de la 
                    # ventana, es necesario redondear a 2 decimales.
                    subtotal = round(ldv.get_subtotal(iva = True), 2)
                    subtotal_siva = round(ldv.get_subtotal(iva = False), 2)
                    beneficio = round(ldv.calcular_beneficio(), 2)
                    costo = round(ldv.calcular_precio_costo()*ldv.cantidad, 2)
                    if ldv.facturaVenta:
                        fac_alb_tic = ldv.facturaVenta.numfactura
                        cobradofra = ldv.facturaVenta.calcular_cobrado()
                        pendientefra = ldv.facturaVenta.calcular_pendiente_cobro()
                        try:
                            fraccion = cobradofra / (cobradofra + pendientefra)
                        except ZeroDivisionError:
                            fraccion = 1.0
                        cobrado = subtotal * fraccion
                        pendiente = subtotal - cobrado
                        beneficio_cobro = beneficio * fraccion
                        costo_cobrado = costo * fraccion
                    elif ldv.albaranSalida:
                        fac_alb_tic = ldv.albaranSalida.numalbaran
                        cobrado = 0.0
                        pendiente = subtotal
                        beneficio_cobro = 0.0
                        costo_cobrado = 0.0
                    elif ldv.ticket:
                        fac_alb_tic = "Ticket %d" % ldv.ticket.numticket
                        cobrado = subtotal
                        pendiente = 0.0
                        beneficio_cobro = beneficio
                        costo_cobrado = costo
                        # Los tickets se asume que se cobran siempre, por 
                        # tanto el costo de los productos sobre lo cobrado 
                        # es del 100%.
                    else:
                        fac_alb_tic = ""
                        cobrado = pendiente = beneficio_cobro = 0.0
                        costo_cobrado = 0.0
                    desc_producto = utils.wrap(ldv.producto.descripcion, 40)
                    try:
                        beneficio_costo = 100.0 * beneficio / costo
                    except ZeroDivisionError:
                        beneficio_costo = 0.0
                    model.append(padre_fec, (desc_producto, 
                                             fac_alb_tic, 
                                             utils.float2str(subtotal), 
                                             utils.float2str(subtotal_siva), 
                                             "%s (%s%%)" % (
                                                utils.float2str(beneficio), 
                                                utils.float2str(
                                                    beneficio_costo)), 
                                             "LDV:%d" % ldv.id))
                    # Actualizo totales en memoria y en nodos padre TreeView
                    totfact += subtotal
                    totsiniva += subtotal_siva
                    totbeneficio += beneficio
                    totbeneficio_cobro += beneficio_cobro
                    totcobrado += cobrado
                    totpendiente += pendiente
                    total_costo += costo
                    total_costo_cobrado += costo_cobrado
                    model[padre_fec][2] = utils.float2str(
                                            utils._float(model[padre_fec][2]) 
                                                         + subtotal)
                    model[padre_fec][3] = utils.float2str(
                                            utils._float(model[padre_fec][3]) 
                                                         + subtotal_siva)
                    model[padre_fec][4] = utils.float2str(
                                            utils._float(model[padre_fec][4]) 
                                                         + beneficio)
                    model[padre_mat][2] = utils.float2str(
                                            utils._float(model[padre_mat][2]) 
                                                         + subtotal)
                    model[padre_mat][3] = utils.float2str(
                                            utils._float(model[padre_mat][3]) 
                                                         + subtotal_siva)
                    model[padre_mat][4] = utils.float2str(
                                            utils._float(model[padre_mat][4]) 
                                                         + beneficio)
        self.rellenar_totales(totfact, totsiniva, totbeneficio, 
                              totcobrado, totpendiente, totbeneficio_cobro, 
                              total_costo, total_costo_cobrado)
        self.wids['tv_datos'].set_model(model)
        self.wids['tv_datos'].thaw_child_notify()

    def rellenar_tabla_por_proveedor(self, resultados):
        """
        Rellena el model con los items de la consulta
        """        
        model = self.wids['tv_datos'].get_model()
        model.clear()
        totfact = totsiniva = totbeneficio = totbeneficio_cobro = 0.0
        self.wids['tv_datos'].freeze_child_notify()
        self.wids['tv_datos'].set_model(None)
        totcobrado = totpendiente = 0.0
        total_costo = total_costo_cobrado = 0.0
        padres = {}
        for material in resultados:
            for fecha in resultados[material]:
                for ldv in resultados[material][fecha]:
                    # Para que coincidan los totales con la suma de las 
                    # columnas y por coherencia con todas las cifras de la 
                    # ventana, es necesario redondear a 2 decimales.
                    subtotal = round(ldv.get_subtotal(iva = True), 2)
                    subtotal_siva = round(ldv.get_subtotal(iva = False), 2)
                    beneficio = round(ldv.calcular_beneficio(), 2)
                    costo = round(ldv.calcular_precio_costo()*ldv.cantidad, 2)
                    if ldv.facturaVenta:
                        fac_alb_tic = ldv.facturaVenta.numfactura
                        cobradofra = ldv.facturaVenta.calcular_cobrado()
                        pendientefra = ldv.facturaVenta.calcular_pendiente_cobro()
                        try:
                            fraccion = cobradofra / (cobradofra + pendientefra)
                        except ZeroDivisionError:
                            fraccion = 1.0
                        cobrado = subtotal * fraccion
                        pendiente = subtotal - cobrado
                        beneficio_cobro = beneficio * fraccion
                        costo_cobrado = costo * fraccion
                    elif ldv.albaranSalida:
                        fac_alb_tic = ldv.albaranSalida.numalbaran
                        cobrado = 0.0
                        pendiente = subtotal
                        beneficio_cobro = 0.0
                        costo_cobrado = 0.0
                    elif ldv.ticket:
                        fac_alb_tic = "Ticket %d" % ldv.ticket.numticket
                        cobrado = subtotal
                        pendiente = 0.0
                        beneficio_cobro = beneficio
                        costo_cobrado = costo
                        # Los tickets se asume que se cobran siempre, por 
                        # tanto el costo de los productos sobre lo cobrado 
                        # es del 100%.
                    else:
                        fac_alb_tic = ""
                        cobrado = pendiente = beneficio_cobro = 0.0
                        costo_cobrado = 0.0
                    desc_producto = utils.wrap(ldv.producto.descripcion, 40)
                    try:
                        beneficio_costo = 100.0 * beneficio / costo
                    except ZeroDivisionError:
                        beneficio_costo = 0.0
                    proveedor = ldv.get_proveedor()
                    try:
                        padre = padres[proveedor]
                    except KeyError:
                        padre = padres[proveedor] = model.append(None, 
                            (proveedor and proveedor.nombre 
                                or "Sin proveedor", 
                             "-", 
                             utils.float2str(0.0), 
                             utils.float2str(0.0), 
                             utils.float2str(0.0),  
                             proveedor and proveedor.get_puid() or ""
                            ))
                    model.append(padre, (desc_producto, 
                                         fac_alb_tic, 
                                         utils.float2str(subtotal), 
                                         utils.float2str(subtotal_siva), 
                                         "%s (%s%%)" % (
                                            utils.float2str(beneficio), 
                                            utils.float2str(
                                                    beneficio_costo)), 
                                         ldv.get_puid()
                                        ))
                    # Actualizo totales en memoria y en nodos padre TreeView
                    totfact += subtotal
                    totsiniva += subtotal_siva
                    totbeneficio += beneficio
                    totbeneficio_cobro += beneficio_cobro
                    totcobrado += cobrado
                    totpendiente += pendiente
                    total_costo += costo
                    total_costo_cobrado += costo_cobrado
                    model[padre][2] = utils.float2str(
                                            utils._float(model[padre][2]) 
                                                         + subtotal)
                    model[padre][3] = utils.float2str(
                                            utils._float(model[padre][3]) 
                                                         + subtotal_siva)
                    model[padre][4] = utils.float2str(
                                            utils._float(model[padre][4]) 
                                                         + beneficio)
        self.rellenar_totales(totfact, totsiniva, totbeneficio, 
                              totcobrado, totpendiente, totbeneficio_cobro, 
                              total_costo, total_costo_cobrado)
        self.wids['tv_datos'].set_model(model)
        self.wids['tv_datos'].thaw_child_notify()

    def rellenar_totales(self, 
                         total_facturado, 
                         total_siniva, 
                         total_beneficio, 
                         total_cobrado, 
                         total_pendiente_de_cobro, 
                         total_beneficio_de_lo_cobrado, 
                         total_costo, 
                         total_costo_cobrado):
        """
        Introduce los totales en los "entries".
        """
        self.wids['e_total'].set_text(utils.float2str(total_facturado))
        self.wids['e_siniva'].set_text(utils.float2str(total_siniva))
        try:
            beneficio = total_beneficio * 100.0 / total_siniva
        except ZeroDivisionError:
            beneficio = 0
        try:
            beneficio_sobre_costo = total_beneficio * 100.0 / total_costo
        except ZeroDivisionError:
            beneficio_sobre_costo = 0
        try:
            beneficio_cobro = (total_beneficio_de_lo_cobrado * 100.0 
                                / total_cobrado)
        except ZeroDivisionError:
            beneficio_cobro = 0
        try:
            beneficio_cobro_sobre_costo = (100 * 
                total_beneficio_de_lo_cobrado / total_costo_cobrado)
        except ZeroDivisionError:
            beneficio_cobro_sobre_costo = 0
        #self.wids['e_beneficio'].set_text("%s (%s%% de las ventas; %s%% sobre precio defecto)" % (
        self.wids['e_beneficio'].set_text("%s (%s%% sobre precio defecto)" % (
            utils.float2str(total_beneficio), 
            utils.float2str(beneficio_sobre_costo, 2, autodec = True)))
        #self.wids['e_beneficio_cobro'].set_text("%s (%s%% de lo cobrado; %s%% sobre precio defecto en cobros)" % (
        self.wids['e_beneficio_cobro'].set_text("%s (%s%% sobre precio defecto en cobros)" % (
            utils.float2str(total_beneficio_de_lo_cobrado), 
            utils.float2str(beneficio_cobro_sobre_costo, 2, autodec = True)))
        self.wids['e_cobrado'].set_text(utils.float2str(total_cobrado))
        self.wids['e_pendiente'].set_text(
            utils.float2str(total_pendiente_de_cobro))

    def set_inicio(self, boton):
        temp = utils.mostrar_calendario(fecha_defecto = self.inicio, padre = self.wids['ventana'])
        self.inicio = mx.DateTime.DateTimeFrom(day = temp[0], month = temp[1], year = temp[2])
        self.wids['e_fechainicio'].set_text(utils.str_fecha(self.inicio))
        self.fin = self.inicio
        self.wids['e_fechafin'].set_text(utils.str_fecha(self.fin))

    def set_fin(self, boton):
        temp = utils.mostrar_calendario(fecha_defecto = self.fin, padre = self.wids['ventana'])
        self.fin = temp
        self.fin = mx.DateTime.DateTimeFrom(day = temp[0], month = temp[1], year = temp[2])
        self.wids['e_fechafin'].set_text(utils.str_fecha(self.fin))

    def buscar(self,boton):
        """
        Dadas fecha de inicio y de fin, busca todas las LDV de 
        tickets sin factura (ni albarán, lógicamente).
        OJO: NO CUENTA SERVICIOS.
        """
        vpro = ventana_progreso.VentanaProgreso(padre = self.wids['ventana'])
        vpro.mostrar()
        inicio = self.inicio
        fin = self.fin
        LDV = pclases.LineaDeVenta
        FV = pclases.FacturaVenta
        AS = pclases.AlbaranSalida
        T = pclases.Ticket
        ldvst = LDV.select(pclases.AND(LDV.q.ticketID == T.q.id, 
                    LDV.q.albaranSalidaID == None, 
                    LDV.q.facturaVentaID == None, 
                    T.q.fechahora >= inicio, 
                    T.q.fechahora < fin + mx.DateTime.oneDay))
        self.resultados = {}
        act = 0.0; tot = ldvst.count()
        for ldv in ldvst:
            vpro.set_valor(act/tot, "Calculando beneficio tickets...")
            add_ldv_a_diccionario_resultados(ldv, self.resultados)
            act += 1
        vpro.set_valor(1.0, "Calculando totales...")
        if self.wids['rb_por_familia'].get_active():
            self.rellenar_tabla(self.resultados)
        elif self.wids['rb_por_ticket'].get_active():
            self.rellenar_tabla_por_ticket(self.resultados)
        elif self.wids['rb_por_proveedor'].get_active():
            self.rellenar_tabla_por_proveedor(self.resultados)
        vpro.ocultar()

    def imprimir(self, boton):
        """
        Prepara la vista preliminar para la impresión del informe.
        """
        resp = utils.dialogo(titulo = "¿IMPRIMIR DESGLOSE?", 
                             texto = "Puede imprimir un resumen o todo el "
                                     "contenido de la consulta\n"
                                     "¿Desea imprimir toda la información "
                                     "desglosada?", 
                             padre = self.wids['ventana'])
        if resp:
            tv = self.wids['tv_datos']
            tv.expand_all()
            while gtk.events_pending(): gtk.main_iteration(False)
            colstotales = []
        else:
            tv = self.wids['tv_datos']
            tv.collapse_all()
            while gtk.events_pending(): gtk.main_iteration(False)
            from consulta_ventas_por_producto import convertir_a_listview
            tv = convertir_a_listview(tv)
            colstotales = [2, 3, 4]
        strfecha = "De %s a %s" % (self.wids['e_fechainicio'].get_text(), 
                                   self.wids['e_fechafin'].get_text())
        abrir_pdf(treeview2pdf(tv, 
                               titulo = "Beneficio sobre tarifa (tickets)", 
                               fecha = strfecha, 
                               numcols_a_totalizar = colstotales))

    def exportar(self, boton):
        """
        Exporta el TreeView a CSV.
        """
        abrir_csv(treeview2csv(self.wids['tv_datos']))


def add_ldv_a_diccionario_resultados(ldv, r):
    if ldv.productoCompra:
        material = ldv.productoCompra.tipoDeMaterial
    else:
        material = None
    if material not in r:
        r[material] = {}
    if ldv.facturaVenta:
        fecha = ldv.facturaVenta.fecha
    elif ldv.albaranSalida:
        fecha = ldv.albaranSalida.fecha
    elif ldv.ticket:
        fecha = utils.abs_mxfecha(ldv.ticket.fechahora)
    else:
        fecha = None
    if fecha not in r[material]:
        r[material][fecha] = [ldv]
    else:
        r[material][fecha].append(ldv)

if __name__ == '__main__':
    t = ConsultaBeneficioSoloTickets()

