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
## partes_de_fabricacion_rollos.py - Parte de producción para rollos. 
###################################################################
## NOTAS:
##  
## ----------------------------------------------------------------
##  
###################################################################
## Changelog:
## 15 de noviembre de 2005 -> Inicio
## 16 de noviembre de 2005 -> 99% funcional
## 23 de enero de 2006 -> Portado a clase.
## 26 de enero de 2006 -> Funcional al 99% one more time.
## 9 de mayo de 2006 -> Control de permisos. Para copiar a otras 
## ventanas, mirar: check_permisos(), rellenar_widgets, 
## self.__lecturaescritura, self.__permisos, activar_widgets y 
## la asignación de id en nuevo_.
## 10 de mayo de 2006 -> Cambiado comportamiento de set_articulo.
## 26 de julio de 2006 -> Añadidos empleados por defecto según 
##                        calendario laboral.
## 8 de marzo de 2006 -> Añado rollos por defecto.
## 31 de julio de 2007 -> Nueva casilla "versión de la ficha de 
##                        producción" usada (texto libre).
###################################################################
## DONE:
## + Comprobar que se marca bien el consumo estimado en relación 
##   con el de balas _en todos los partes_ de la misma partida. 
## + No estaría de más un entry con el cálculo acumulado de consumo 
##   estimado (además facilitaría el consumo en relación con 
##   el consumo real de balas añadida. El cálculo de arriba, 
##   vamos.)
## + Falta cálculo de rendimiento: 
##   nºtrabajadores * horas turno / nº trabajadores * horas reales.
## + Comprobar que las horas del parte no pisan a otro parte de rollos.
## + Al eliminar todos los rollos de un parte, los consumos deberían 
##   quedar a 0. Sin embargo no es así. Why? (por poner el parte a 
##   None antes de descontar el consumo).
###################################################################


#import sys, os
#sys.stdout = open("salida_debug.txt", "a")

from ventana import Ventana
import utils
import pygtk
pygtk.require('2.0')
import gtk, gtk.glade, time #, sqlobject   ## pclases enmascara sqlobject. No 
                                        ## hace falta importarlo directamente.
try:
    import pclases
except ImportError:
    import sys
    from os.path import join as pathjoin; sys.path.append(pathjoin("..", "framework"))
    import pclases
import mx
try:
    import geninformes
except ImportError:
    import sys
    sys.path.append('../informes')
    import geninformes
from utils import _float as float
try:
    import psycopg
except ImportError:
    import psycopg2 as psycopg
from ventana_progreso import VentanaActividad, VentanaProgreso
import re, os
from partes_de_fabricacion_balas import verificar_solapamiento, \
                                        buscar_o_crear_albaran_interno, \
                                        entran_en_turno
try:
    from psycopg import ProgrammingError as psycopg_ProgrammingError
except ImportError:
    from psycopg2 import ProgrammingError as psycopg_ProgrammingError

def build_etiqueta(rollo):
    """
    Devuelve un diccionario con la información del rollo a incluir en la 
    etiqueta.
    Si rollo no es un rollo o un rollo defectuoso, devuelve None.
    También devuelve la función que genera el modelo de etiqueta que le 
    corresponde al producto.
    """
    try:
        cer = rollo.productoVenta.camposEspecificosRollo
        func = cer.modeloEtiqueta.get_func()
    except AttributeError:  # No es un rollo.
        func = None
    except ValueError:      # No tiene modelo de etiqueta.
        func = None
    if isinstance(rollo, pclases.RolloDefectuoso):
        producto = rollo.productoVenta
        res = {'descripcion': producto.nombre,
               'densidad': utils.float2str(rollo.densidad, 1),
               'ancho': "%s m" % (utils.float2str(rollo.ancho, 1)),
               'peso': "%s kg" % (utils.float2str(
                                    rollo.peso - rollo.pesoEmbalaje)),
               'm2': "%s m²" % (utils.float2str(
                                    rollo.ancho * rollo.metrosLineales, 1)),
               'mlin': "%s m" % (utils.float2str(rollo.metrosLineales)),
               #'nrollo': str(rollo.numrollo),
               'nrollo': rollo.codigo,     # Para diferenciarlos mejor en la 
                    # etiqueta desde lejos (aunque lleven otras marcas y tal)
               'partida': rollo.partida.codigo, 
               'codigo': producto.codigo, 
               'codigo39': rollo.codigo, 
               'defectuoso': True, 
               'idrollo': rollo.id, 
               'objeto': rollo} 
    elif isinstance(rollo, pclases.Rollo):
        producto = rollo.productoVenta
        campos = producto.camposEspecificosRollo
        if rollo.rollob:
            res = {'descripcion': producto.nombre,
                   'densidad': str(campos.gramos),
                   'ancho': "%s m" % (campos.ancho),
                   'peso': "%s kg" % (int(
                    (campos.ancho*campos.metrosLineales*campos.gramos/1000))),
                   'm2': "%s m²" % (campos.ancho*campos.metrosLineales),
                   'mlin': "%s m" % (campos.metrosLineales),
                   'nrollo': str(rollo.numrollo),
                   'partida': rollo.partida.codigo, 
                   'codigo': producto.codigo, 
                   'codigo39': rollo.codigo, 
                   'defectuoso': rollo.rollob, 
                   'idrollo': rollo.id, 
                   'objeto': rollo} 
        else:
            res = {'descripcion': producto.nombre,
                   'densidad': str(campos.gramos),
                   'ancho': "%s m" % (campos.ancho),
                   'peso': "%s kg" % (int(
                        (campos.metros_cuadrados * campos.gramos / 1000.0))),
                        # PESO TEÓRICO. Sin embalaje.
                   'm2': "%s m²" % (campos.metros_cuadrados),
                   'mlin': "%s m" % (campos.metrosLineales),
                   'nrollo': str(rollo.numrollo),
                   'partida': rollo.partida.codigo, 
                   'codigo': producto.codigo, 
                   'codigo39': rollo.codigo,
                   'defectuoso': False, 
                   'idrollo': rollo.id, 
                   'objeto': rollo}    # Si todavía no se ha creado, como 
                        # defectuoso == False, geninformes no lo necesitará.
    else:
        res = None
    return res, func

def imprimir_etiqueta_de_rollo_defectuoso(rollo):
    """
    Imprime una etiqueta de rollo defectuoso correspondiente 
    al objeto rollo/rolloDefectuoso recibido.
    """
    import informes
    producto = rollo.productoVenta
    if isinstance(rollo, pclases.RolloDefectuoso):
        elemento = {'descripcion': producto.nombre,
                    'densidad': utils.float2str(rollo.densidad, 1),
                    'ancho': "%s m" % (utils.float2str(rollo.ancho, 1)),
                    'peso': "%s kg" % (utils.float2str(rollo.peso - rollo.pesoEmbalaje)),
                    'm2': "%s m²" % (utils.float2str(rollo.ancho * rollo.metrosLineales, 1)),
                    'mlin': "%s m" % (utils.float2str(rollo.metrosLineales)),
                    #'nrollo': str(rollo.numrollo),
                    'nrollo': rollo.codigo,     # Para diferenciarlos mejor en 
                            # la etiqueta desde lejos (aunque lleven otras 
                            # marcas y tal)
                    'partida': rollo.partida.codigo, 
                    'codigo': producto.codigo, 
                    'codigo39': rollo.codigo, 
                    'defectuoso': True, 
                    'idrollo': rollo.id, 
                    'objeto': rollo} 
    elif isinstance(rollo, pclases.Rollo):
        campos = producto.camposEspecificosRollo
        elemento = {'descripcion': producto.nombre,
                    'densidad': str(campos.gramos),
                    'ancho': "%s m" % (campos.ancho),
                    'peso': "%s kg" % (int((campos.ancho*campos.metrosLineales*campos.gramos/1000))),
                    'm2': "%s m²" % (campos.ancho*campos.metrosLineales),
                    'mlin': "%s m" % (campos.metrosLineales),
                    'nrollo': str(rollo.numrollo),
                    'partida': rollo.partida.codigo, 
                    'codigo': producto.codigo, 
                    'codigo39': rollo.codigo, 
                    'defectuoso': rollo.rollob, 
                    'idrollo': rollo.id, 
                    'objeto': rollo} # En realidad da igual, porque si rollob 
                        # es True se cambiarán todos estos datos antes de 
                        # imprimir su etiqueta.
    else:
        return
    informes.abrir_pdf(geninformes.etiquetasRollosEtiquetadora([elemento], 
                                                               False))
    

class PartesDeFabricacionRollos(Ventana):
    def __init__(self, objeto = None, permisos = "rwx", usuario = None):
        """
        Constructor. objeto puede ser un objeto de pclases con el que
        comenzar la ventana (en lugar del primero de la tabla, que es
        el que se muestra por defecto).
        """
        self.usuario = usuario
        self.producto = None    # Producto relacionado con el parte. 
			                	# Debe coincidir con el de todas las rollos 
                                # de "Detalles de producción"
        self.ultima_etiqueta = None
        self.__lecturaescritura = None
            # Este atributo vale None cuando la ventana permite acceder y 
            # modificar todos los partes.
            # Si sólo permite consulta de partes anteriores y edición de los 
            # nuevos, self.__lecturaescritura contiene el identificador del 
            # parte. De este modo siempre se puede cambiar el parte nuevo 
            # aunque se haya consultado momentáneamente otro.
        self.__permisos = permisos
        # ¡Mira papá lo que me acabo de inventar! ¡Sin manos! si el permiso 
        # contiene "x" la ventana permite crear nuevos partes. Si tiene "r" 
        # permite leer partes antiguos. Y si contiene "w" permite editar 
        # partes antiguos. Ueeee.
        Ventana.__init__(self, 'partes_de_fabricacion_rollos.glade', objeto)
        # XXX
        self.wids['sp_merma'] = gtk.SpinButton()
        self.wids['sp_merma'].set_range(0, 100)
        self.wids['table1'].attach(self.wids['sp_merma'], 1, 2, 1, 2)
        self.wids['sp_merma'].connect('output', 
                                      self.actualizar_consumo_estimado)
        self.wids['sp_merma'].set_property("visible", False)
        # XXX
        connections = {'b_salir/clicked': self._salir,
                       'ventana/delete_event' : self._salir,
                       'b_nuevo/clicked': self.crear_nuevo_partedeproduccion,
                       'b_actualizar/clicked': self.actualizar_ventana,
                       'b_guardar/clicked': self.guardar,
                       'b_buscar/clicked': self.buscar_partedeproduccion,
                       'b_borrar/clicked': self.borrar_parte,
                       'b_articulo/clicked': self.set_articulo,
                       'b_fecha/clicked': self.mostrar_calendario,
                       'b_hora_fin/clicked': self.set_hora_final,
                       'b_hora_ini/clicked': self.set_hora_inicial,
                       'b_add_rollo/clicked': self.add_rollo,
                       'b_drop_rollo/clicked': self.drop_rollo,
                       'b_add_incidencia/clicked': self.add_incidencia,
                       'b_drop_incidencia/clicked': self.drop_incidencia,
                       'b_cambiar_partida/clicked': self.cambiar_partida,
                       'b_add_bala/clicked': self.add_bala,
                       'b_drop_bala/clicked': self.drop_bala,
                       'b_add_empleado/clicked': self.add_empleado,
                       'b_drop_empleado/clicked': self.drop_empleado,
                       'ch_bloqueado/clicked': self.bloquear,
                       'b_plastico/clicked': self.cambiar_plastico,
                       'b_imprimir/clicked': self.imprimir,  
                       'b_etiquetas/clicked': self.etiquetas,  
                       'b_etiq_peq/clicked': self.etiquetas,
                       'b_add_agujas/clicked': self.add_agujas,
                       'b_drop_agujas/clicked': self.drop_agujas, 
                       'b_bascula/clicked': self.iniciar_pesaje_auto, 
                       'b_add_desecho/clicked': self.add_desecho, 
                       'b_drop_desecho/clicked': self.drop_desecho, 
                       'b_add_consumo/clicked': self.consumir_manual
                      }  
        self.add_connections(connections)
        linea = pclases.LineaDeProduccion.select(
            pclases.LineaDeProduccion.q.nombre.contains('de geotextiles'))
        if linea.count() == 0:
            print "WARNING: La línea de geotextiles no está correctamente "\
                  "dada de alta."
            self.plastico = None
            self.linea = None
        else:
            linea = linea[0]
            self.linea = linea
            formulacion = linea.formulacion
            try:
                self.plastico = [ca.productoCompra 
                                 for ca in formulacion.consumosAdicionales 
                                     if "plastico" in ca.nombre 
                                         and not ca.productoCompra.obsoleto][0]
            except IndexError:
                self.plastico = None
            # Como ahora el consumo de plástico es manual, si el 
            # consumoAdicional no existe o no tiene asociado un 
            # producto de compra o ningún producto de venta lo usa, 
            # oculto el botón de selección de plástico de 
            # envolver porque en ese caso no vale para nada.
            consumoautomaticoplastico = [ca for ca 
                in formulacion.consumosAdicionales if "plastico" in ca.nombre]
            if consumoautomaticoplastico == []:
                ver_consumo_plastico = False
            else:
                ver_consumo_plastico = True
                for ca in consumoautomaticoplastico:
                    ver_consumo_plastico = (ver_consumo_plastico 
                        and ca.productoCompra != None 
                        and not ca.productoCompra.obsoleto
                        and ca.productosVenta != [])
            self.wids['hbox14'].set_property("visible", ver_consumo_plastico)
        self.inicializar_ventana()
        if self.objeto == None:
            self.ir_a_primero()
        else:
            self.ir_a(objeto)
        gtk.main()

    # --------------- Funciones auxiliares ------------------------------
    def es_diferente(self):
        """
        Devuelve True si la información en pantalla es distinta a la
        del objeto en memoria.
        """
        partedeproduccion = self.objeto
        if partedeproduccion == None: 
            return False	# Si no hay partedeproduccion activo, devuelvo que no hay cambio respecto a la ventana
        try:
            condicion = utils.str_fecha(partedeproduccion.fecha) == self.wids['e_fecha'].get_text()
            condicion = condicion and (str(partedeproduccion.prodestandar) == self.wids['e_o11'].get_text())
            condicion = condicion and (self.wids['e_fichaproduccion'].get_text() == partedeproduccion.fichaproduccion)
            # NOTA: Nada más a comparar. La info del artículo es la de alguno de las rollos introducidas y se elige mediante el botón 
            # correspondiente (determinará las búsquedas y la información a pedir a la hora de añadir rollos en "detalles de producción".)
            obs = partedeproduccion.observaciones
            bounds = self.wids['txt_observaciones'].get_buffer().get_bounds()
            condicion = condicion and (self.wids['txt_observaciones'].get_buffer().get_text(bounds[0], bounds[1]) == obs)
            condicion = condicion and (self.wids['sp_merma'].get_value() / 100.0 == partedeproduccion.merma)
            condicion = condicion and (partedeproduccion.horainicio.strftime('%H:%M') == self.wids['e_hora_ini'].get_text())
            condicion = condicion and (partedeproduccion.horafin.strftime('%H:%M') == self.wids['e_hora_fin'].get_text())
        except AttributeError, msg:
            txt = "%s: partes_de_fabricacion_rollos.py::es_diferente -> Devuelvo True; Excepción 'AttributeError': %s" % (self.usuario, msg)
            self.logger.error(txt)
            partedeproduccion.sync()  # Si la excepción es por lo que pienso, al sincronizar se actualizarán las horas como mx y no como str.
            condicion = False
        return not condicion	# Condición verifica que sea igual

    def colorear_rollos(self, tv):
        def cell_func(column, cell, model, itr, numcol):
            cell.set_property("foreground", None)   # Colores por defecto. Si no se cumple nada de lo de abajo, es como debe estar la fila.
            cell.set_property("cell-background", None)  
            if self.producto != None and model[itr][1] != None and model[itr][1].strip() != "":
                if model[itr][3] < self.producto.camposEspecificosRollo.gramos:
                    color = "blue"
                elif model[itr][3] == self.producto.camposEspecificosRollo.gramos:
                    color = "green"
                else:
                    color = "red"
                if numcol == 3:  # Columna de la densidad
                    cell.set_property("foreground", color)  # En windows GTK no es capaz de sombrear los colores. Directamente no se muestra.
                    cell.set_property("text", "%.1f" % model[itr][3])
                ## Redondeo de decimales:
                if numcol == 2:
                    cell.set_property("text", "%.1f" % model[itr][2])
                # Marco el color de fondo para las muestras:
                id = model[itr][-1]
                try:
                    articulo = pclases.Articulo.get(id)
                    if articulo.es_rollo():
                        rollo = articulo.rollo
                        if rollo.muestra:
                            cell.set_property("cell-background", "grey")
                        elif rollo.rollob:
                            cell.set_property("cell-background", "IndianRed")
                        else:
                            cell.set_property("cell-background", "white")
                    elif articulo.es_rollo_defectuoso():
                        cell.set_property("cell-background", "orange red")
                except pclases.SQLObjectNotFound, msg:
                    pass
            elif model[itr][5].strip() != "":
                cell.set_property("text", model[itr][numcol])
                cell.set_property("foreground", "saddle brown")
            else:
                cell.set_property("text", model[itr][numcol])
                cell.set_property("foreground", None)

        cols = tv.get_columns()
        for i in xrange(len(cols)):
            column = cols[i]
            cells = column.get_cell_renderers()
            for cell in cells:
                column.set_cell_data_func(cell, cell_func, i)
    
    def colorear_tabla_empleados(self):
        """
        Prepara y asocia la función para resaltar los empleados 
        cuyas horas trabajadas sean inferiores o superiores a 
        la duración del parte.
        """
        def cell_func(column, cell, model, itr, numcol):
            idht = model[itr][-1]
            ht = pclases.HorasTrabajadas.get(idht)
            duracion_parte = self.objeto.get_duracion()
            ht_horas = ht.horas
            try:
                supera_parte = ht_horas > duracion_parte
            except TypeError:   # ht.horas es datetime.time
                ht_horas = utils.DateTime2DateTimeDelta(ht_horas)
                supera_parte = ht_horas > duracion_parte
            if supera_parte:
                color = "orange"
            elif ht_horas < duracion_parte:
                color = "red"
            else:
                color = "black"
            cell.set_property("foreground", color)

        cols = self.wids['tv_empleados'].get_columns()
        numcol = len(cols) - 1
        column = cols[numcol]
        cells = column.get_cell_renderers()
        for cell in cells:
            column.set_cell_data_func(cell, cell_func, numcol)

    def inicializar_ventana(self):
        """
        Inicializa los controles de la ventana, estableciendo sus
        valores por defecto, deshabilitando los innecesarios,
        rellenando los combos, formateando el TreeView -si lo hay-...
        """
        # CWT: No se debe poder editar la producción estándar desde el parte. 
        # Siempre debe ser la del producto, so...
        self.wids['e_o11'].set_has_frame(False)
        self.wids['e_o11'].set_property("editable", False)
        self.wids['e_o11'].set_property("editable", True)   # NOTA: XXX: Hasta 
                    # que estén bien puestas todas las producciones estándar.
        # Inicialmente no se muestra NADA. Sólo se le deja al
        # usuario la opción de buscar o crear nuevo.
        self.activar_widgets(False)
        self.wids['b_actualizar'].set_sensitive(False)
        self.wids['b_guardar'].set_sensitive(False)
        self.wids['b_nuevo'].set_sensitive(True)
        self.wids['b_buscar'].set_sensitive(True)
        self.wids['e_num_a'].set_alignment(1.0)
        self.wids['e_num_b'].set_alignment(1.0)
        self.wids['e_peso_a'].set_alignment(1.0)
        self.wids['e_peso_b'].set_alignment(1.0)
        self.wids['e_peso_sin_a'].set_alignment(1.0)
        self.wids['e_peso_sin_b'].set_alignment(1.0)
        self.wids['e_metros_a'].set_alignment(1.0)
        self.wids['e_metros_b'].set_alignment(1.0)
        self.wids['e_mlin_a'].set_alignment(1.0)
        self.wids['e_mlin_b'].set_alignment(1.0)
        # Inicialización del resto de widgets:
        # (Nombre, tipo, editable, ordenable, buscable, función_actualización)
        cols = (('Partida', 'gobject.TYPE_STRING', False, True, False, None),
                ('Nº Rollo', 'gobject.TYPE_STRING', False, True, True, None),
                ('Peso c.e.(kg)', 'gobject.TYPE_FLOAT', True, True, False, 
                 self.cambiar_peso),
                ('gr/m² (s.e.)', 'gobject.TYPE_FLOAT', False, True, False, 
                 None),
                ('Motivo parada', 'gobject.TYPE_STRING', False, True, False, 
                 self.cambiar_motivo_incidencia),
                ('Hora comienzo', 'gobject.TYPE_STRING', True, True, False, 
                 self.cambiar_inicio_incidencia),
                ('Hora terminación', 'gobject.TYPE_STRING', True, True, False, 
                 self.cambiar_fin_incidencia),
                ('Duración', 'gobject.TYPE_STRING', False, True, False, None),
                ('Observaciones', 'gobject.TYPE_STRING', True, False, False, 
                 self.cambiar_observaciones),
                ('ID', 'gobject.TYPE_INT64', False, False, False, None)
               )
        utils.preparar_listview(self.wids['tv_rollos'], cols)
        self.colorear_rollos(self.wids['tv_rollos'])
        self.wids['tv_rollos'].get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        self.wids['tv_rollos'].add_events(gtk.gdk.BUTTON_PRESS_MASK)
        self.wids['tv_rollos'].connect('button_press_event', 
                                       self.button_clicked) 
        cols = (('Código', 'gobject.TYPE_INT64', False, True, False, None),
                ('Nombre', 'gobject.TYPE_STRING', False, True, False, None),
                ('Apellidos', 'gobject.TYPE_STRING', False, True, True, None),
                ('Horas', 'gobject.TYPE_STRING', True, True, False, 
                    self.cambiar_horas_trabajadas),
                ('ID', 'gobject.TYPE_INT64', False, False, False, None))
        utils.preparar_listview(self.wids['tv_empleados'], cols)
        self.colorear_tabla_empleados()
        cols = (('Nº Bala', 'gobject.TYPE_STRING', False, True, True, None),
                ('Peso', 'gobject.TYPE_FLOAT', True, True, False, 
                 self.cambiar_peso_bala),
                ('ID', 'gobject.TYPE_INT64', False, False, False, None))
        utils.preparar_listview(self.wids['tv_balas'], cols)
        # Al loro porque me voy a cargar la mitad de lo que ha hecho el 
        # preparar_listview.
        import gobject
        model = gtk.ListStore(gobject.TYPE_STRING, 
                              gobject.TYPE_FLOAT, 
                              gobject.TYPE_FLOAT, 
                              gobject.TYPE_INT64)
        self.wids['tv_balas'].set_model(model)
        self.wids['tv_balas'].get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        cell = gtk.CellRendererProgress()
        column = gtk.TreeViewColumn('Consumido', cell)
        column.add_attribute(cell, 'value', 2)
        column.set_sort_column_id(2)
        self.wids['tv_balas'].insert_column(column, 2) 
        cols = (('Producto', 'gobject.TYPE_STRING', False, True, True, None),
                ('Cantidad', 'gobject.TYPE_INT64', True, True, False, 
                    self.cambiar_cantidad_aguja),
                ('ID', 'gobject.TYPE_INT64', False, False, False, None))
        utils.preparar_listview(self.wids['tv_agujas'], cols)
        cols = (('Producto', 'gobject.TYPE_STRING', False, True, True, None), 
                ('Cantidad', 'gobject.TYPE_STRING', False, True, False, None), 
                ('ID', 'gobject.TYPE_INT64', False, False, False, None))
        utils.preparar_listview(self.wids['tv_consumos'], cols)
        cols = (('Producto', 'gobject.TYPE_STRING', False, True, True, None), 
                ('Cantidad', 'gobject.TYPE_STRING', True, True, False, 
                    self.cambiar_cantidad_descuento_material), 
                ('Observaciones', 'gobject.TYPE_STRING', True, True, False, 
                    self.cambiar_observaciones_descuento_material), 
                ('ID', 'gobject.TYPE_INT64', False, False, False, None))
        utils.preparar_listview(self.wids['tv_desecho'], cols)
        self.wids['tv_desecho'].get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        self.wids['ventana'].maximize()

    def cambiar_observaciones_descuento_material(self, cell, path, newtext):
        """
        Cambia las observaciones del registro.
        """
        model = self.wids['tv_desecho'].get_model()
        id = model[path][-1]
        desecho = pclases.DescuentoDeMaterial.get(id)
        desecho.observaciones = newtext
        desecho.fechahora = mx.DateTime.localtime()     # Actualizo la fecha y hora.
        self.objeto.unificar_desechos()
        self.rellenar_tabla_desechos()

    def cambiar_cantidad_descuento_material(self, cell, path, newtext):
        """
        Cambia la cantidad descontada del registro y actualiza el 
        producto de venta a la nueva cantidad (suma la cantidad 
        anterior y resta la nueva).
        """
        model = self.wids['tv_desecho'].get_model()
        id = model[path][-1]
        desecho = pclases.DescuentoDeMaterial.get(id)
        try:
            newtext=newtext.replace(desecho.productoCompra.unidad, "").strip()
            nueva_cantidad = utils._float(newtext)
        except ValueError:
            utils.dialogo_info(titulo = "ERROR FORMATO NUMÉRICO", 
                texto = 'El texto "%s" no es una cantidad correcta.' % newtext,
                padre = self.wids['ventana'])
        else:
            cantidad_desecho_inicial = desecho.cantidad
            productoCompra = desecho.productoCompra
            productoCompra.sync()
            antes = productoCompra.existencias
            cantidad_desecho_final = desecho.cambiar_cantidad(nueva_cantidad)
            despues = desecho.productoCompra.existencias
            self.logger.warning("%spartes_de_fabricacion_rollos::cambiar_cantidad_descuento_material -> Cambiada cantidad de descuento existente. Stock de %s antes: %f, después: %f. Cantidad de desecho antes: %f. Después: %f." % (self.usuario and self.usuario.usuario + ": " or "", productoCompra.descripcion, antes, despues, cantidad_desecho_inicial, cantidad_desecho_final))
            if cantidad_desecho_final != nueva_cantidad:
                utils.dialogo_info(titulo = "EXISTENCIAS INSUFICIENTES", 
                                   texto = "No había existencias suficientes del producto para cambiar la\ncantidad desechada a %s." % (utils.float2str(nueva_cantidad)), 
                                   padre = self.wids['ventana'])
            self.objeto.unificar_desechos()
            self.rellenar_tabla_desechos()

    def actualizar_consumo(self, consumo, descontar):
        """
        Pone el campo actualizado del consumo a True y 
        descuenta la cantidad del producto de compra.
        """
        consumo.actualizado = descontar 
        if descontar:
            consumo.productoCompra.existencias -= consumo.cantidad
            consumo.productoCompra.add_existencias(
                -consumo.cantidad, 
                pclases.Almacen.get_almacen_principal()) 
        else:
            consumo.productoCompra.existencias += consumo.cantidad
            consumo.productoCompra.add_existencias(
                consumo.cantidad, 
                pclases.Almacen.get_almacen_principal()) 

    def add_agujas(self, b):
        """ DEPRECATED """
        producto = self.buscar_producto_compra("AGUJA")
        if producto == None or producto.obsoleto:
            return
        cantidad = utils.dialogo_entrada(titulo = 'CANTIDAD', 
                                texto = 'Introduzca la cantidad consumida:', 
                                padre = self.wids['ventana'])
        if cantidad == None:
            return
        try:
            cantidad = float(cantidad)
        except ValueError:
            utils.dialogo_info(titulo = "ERROR", 
                               texto = 'Cantidad incorrecta', 
                               padre = self.wids['ventana'])
            return
        if cantidad > producto.existencias:
            utils.dialogo_info(titulo = 'CANTIDAD INSUFICIENTE', 
                               texto = 'No hay existencias suficientes en '
                                       'almacén.\nVerifique que ha tecleado '
                                       'la cantidad correctamente\ny que las '
                                       'entradas en almacén del producto han '
                                       'sido contabilizadas.', 
                               padre = self.wids['ventana'])
            return
        # NOTA: OJO: (Esto hay que cambiarlo tarde o temprano). Si antes y despues = -3, es consumo de agujas.
        consumo = pclases.Consumo(antes = -3, 
                                  despues = -3,
                                  cantidad = cantidad,
                                  actualizado = False,
                                  parteDeProduccion = self.objeto,
                                  productoCompra = producto)
        self.actualizar_consumo(consumo, True)
        self.objeto.unificar_consumos()
        actualizar_albaran_interno_con_tubos(self.objeto)
        self.rellenar_agujas()
        
    def drop_agujas(self, b):
        """ DEPRECATED """
        model, iter = self.wids['tv_agujas'].get_selection().get_selected()
        if iter == None:
            return
        idconsumo = model[iter][-1]
        consumo = [c for c in self.objeto.consumos if c.id == idconsumo][0]
        self.actualizar_consumo(consumo, False)
        consumo.parteDeProduccion = None
        consumo.destroySelf()
        self.rellenar_agujas()
    
    def cambiar_cantidad_aguja(self, cell, path, texto):
        """ DEPRECATED """
        try:
            cantidad = float(texto)
        except:
            utils.dialogo_info(titulo = "ERROR DE FORMATO", texto = "El texto introducido (%s) no respeta el formato numérico.\nUse solo números y el punto como separador decimal." % texto)
            return
        model = self.wids['tv_agujas'].get_model()
        idc = model[path][-1]
        consumo = pclases.Consumo.get(idc)
        cantidad_anterior = consumo.cantidad
        consumo.productoCompra.existencias += cantidad_anterior
        consumo.productoCompra.add_existencias(
            cantidad_anterior, 
            pclases.Almacen.get_almacen_principal()) 
        consumo.cantidad = cantidad
        model[path][1] = consumo.cantidad
        self.actualizar_consumo(consumo, True)
        cantidad = 0
        for consumo in [c for c in self.objeto.consumos if c.antes == -1 and c.despues == -1]:
            cantidad += consumo.cantidad
        self.wids['e_total_agujas'].set_text(utils.float2str(cantidad, 0))

    def cambiar_cantidad_antes(self, cell, path, texto):
        """ DEPRECATED """
        try:
            antes = float(texto)
        except:
            utils.dialogo_info(titulo = "ERROR DE FORMATO", texto = "El texto introducido (%s) no respeta el formato numérico.\nUse solo números y el punto como separador decimal." % texto, padre = self.wids['ventana'])
            return
        model = self.wids['tv_granza'].get_model()
        idc = model[path][-1]
        consumo = pclases.Consumo.get(idc)
        if antes < consumo.despues or antes < 0:
            utils.dialogo_info(titulo = "ERROR", texto = "La cantidad después de producir no puede ser superior a la de antes de\nempezar la fabricación y ninguna debe ser negativa.", padre = self.wids['ventana'])
            return
        consumo.antes = antes
        consumo.cantidad = consumo.antes - consumo.despues
        model[path][1] = consumo.antes
        model[path][2] = consumo.despues
        model[path][3] = consumo.cantidad
        self.actualizar_consumo(consumo, True)
        cantidad = 0
        for consumo in [c for c in self.objeto.consumos if (c.antes != -1 and c.despues != -1) and (c.antes != -2 and c.despues != -2)]:
            cantidad += consumo.cantidad
        self.wids['e_total_granza'].set_text(utils.float2str(cantidad))
 
    def cambiar_horas_trabajadas(self, cell, path, newtext):
        newtext = newtext.replace(".", ":").replace(",", ":")
        if ":" not in newtext:
            if len(newtext) < 4:
                newtext = ("0" * (4 - len(newtext))) + newtext
            newtext = "%s:%s" % (newtext[:-2], newtext[-2:])
        model = self.wids['tv_empleados'].get_model()
        id = model[path][-1]
        ht = pclases.HorasTrabajadas.get(id)
        try:
            try:
                dtdelta = mx.DateTime.DateTimeDelta(0, float(newtext.split(':')[0]), float(newtext.split(':')[1]), 0)
            except IndexError:
                dtdelta = mx.DateTime.DateTimeDelta(0, int(newtext), 0)
                newtext = utils.str_hora_corta(dtdelta)
            if dtdelta > self.objeto.get_duracion():
                utils.dialogo_info(titulo = "TIEMPO INCORRECTO", texto = "El tiempo trabajado no puede superar la\nduración del parte de producción.", padre = self.wids['ventana'])
                return
            ht.horas = newtext 
            ht.sync(); ht.syncUpdate()
            model[path][3] = ht.horas.strftime('%H:%M')
        except (ValueError, TypeError), msg:
            utils.dialogo_info(titulo = "ERROR", texto = 'El texto "%s" no representa el formato horario.' % newtext, padre = self.wids['ventana'])

    def cambiar_peso_bala(self, cell, path, newtext):
        """ DEPRECATED """
        try:
            peso = float(newtext)
        except:
            utils.dialogo_info(titulo = 'ERROR DE FORMATO', texto = 'No introdujo un número válido', padre = self.wids['ventana'])
            return
        idbala = self.wids['tv_balas'].get_model()[path][-1]
        bala = pclases.Bala.get(idbala)
        bala.pesobala = peso
        self.rellenar_balas()

    def cambiar_peso(self, cell, path, newtext):
        """
        Cambia el peso de un rollo en el ListView de rollos fabricados en el parte.
        """
        if self.usuario == None or self.usuario.nivel <= 2:
            self.cambiar_peso_rollo(cell, path, newtext)
        else:
            utils.dialogo_info(titulo = "SIN PERMISOS", 
                               texto = "No tiene permiso para cambiar el peso de los rollos.", 
                               padre = self.wids['ventana'])

    def activar_widgets(self, s):
        """
        Activa o desactiva (sensitive=True/False) todos 
        los widgets de la ventana que dependan del 
        objeto mostrado.
        Entrada: s debe ser True o False. En todo caso
        se evaluará como boolean.
        """
        s = (s and ((self.usuario and self.usuario.nivel <= 1) 
             or not self.objeto.bloqueado 
             or not self.usuario))
        if self.objeto:
            s = s or self.objeto.id == self.__lecturaescritura
        ws = ('table1', 'tv_rollos', 'hbox1', 'hbox2', 'frame1', 'hbox3', 
              'frame3', 'b_fecha', 'b_hora_ini', 'b_hora_fin', 'b_articulo', 
              'b_add_rollo', 'b_drop_rollo','b_add_incidencia', 
              'b_drop_incidencia', 'b_borrar', 'ch_bloqueado', 'vbox4', 
              'e_fichaproduccion')
        for w in ws:
            self.wids[w].set_sensitive(s)
        # Voy a desactivar el botón para cambiar de producto si el parte ya 
        # tiene asignado una partida donde ya se ha comenzado a producir un 
        # producto. Así evito que haya más de un producto por partida. PERO, 
        # ojo, si el parte actual tiene artículos es que el usuario quiere 
        # cambiar el producto de todos los rollos del parte, entonces sí que 
        # le dejo.
        if self.objeto and self.usuario and self.usuario.nivel > 0:
            codpart = self.wids['e_partida_gtx'].get_text()
            try:
                partida = pclases.Partida.selectBy(codigo = codpart)[0]
            except IndexError:
                pass
            else:
                if partida.get_producto() and not self.objeto.articulos:
                    self.wids['b_articulo'].set_sensitive(False)

    def ir_a_primero(self):
        """
        Pregunta si crear un parte nuevo, de forma que al abrir la ventana
        siempre se pueda empezar un parte de rápidamente.
        Si se contesta que no al diálogo, se va al _último_ registro de la tabla.
        """
        nuevo = False
        if nuevo:
            self.crear_nuevo_partedeproduccion(None)
        else:
            partedeproduccion = self.objeto
            try:
                if partedeproduccion != None: partedeproduccion.notificador.desactivar()
                    # Anulo el aviso de actualización del envío que deja de ser activo.
                # OJO: Debe haber más formas de distinguirlos e incluso más lógicas, pero de momento me voy a guiar  
                # por el formateo de las observaciones. Si tiene 6 campos concatenados con ';' es de balas y si no es de rollos.
                partesdeproduccion = pclases.ParteDeProduccion.select("""partida_cem_id IS NULL AND NOT observaciones LIKE '%;%;%;%;%;%'""")
                partesdeproduccion = partesdeproduccion.orderBy("-id")
                partedeproduccion=partesdeproduccion[0]
                partedeproduccion.notificador.activar(self.aviso_actualizacion)
                    # Activo la notificación
            except:
                partedeproduccion = None 	
            self.objeto = partedeproduccion
            self.actualizar_ventana()

    def refinar_resultados_busqueda(self, resultados):
        """
        Muestra en una ventana de resultados todos los
        registros de "resultados".
        Devuelve el id (primera columna de la ventana
        de resultados) de la fila seleccionada o None
        si se canceló.
        """
        filas_res = []
        for r in resultados:
            filas_res.append((r.id, 
                              utils.str_fecha(r.fecha), 
                              utils.str_hora_corta(r.horainicio), 
                              utils.str_hora_corta(r.horafin),
                              "CLIC PARA VER", 
                              r.observaciones)) 
        idpartedeproduccion = utils.dialogo_resultado(filas_res,
                        titulo = 'Seleccione parte de producción de rollos',
                        cabeceras = ('ID Interno', 
                                     'Fecha', 
                                     'Hora inicio', 
                                     'Hora fin', 
                                     'Partida', 
                                     'Observaciones'),
                        func_change = self.mostrar_info_parte, 
                        padre = self.wids['ventana'])
        if idpartedeproduccion < 0:
            return None
        else:
            return idpartedeproduccion

    def mostrar_info_parte(self, tv):
        model, iter = tv.get_selection().get_selected()
        if iter!=None and model[iter][-2] == "CLIC PARA VER":
            parte = pclases.ParteDeProduccion.get(model[iter][0])   # En los 
                # diálogos de resultado el ID va al revés.
            if parte.es_de_balas() and parte.articulos != []:
                try:
                    lotepartida = parte.articulos[0].bala.lote.codigo
                except AttributeError:
                    lotepartida = parte.articulos[0].bigbag.loteCem.codigo
            elif not parte.es_de_balas() and parte.articulos != []:
                lotepartida = parte.articulos[0].partida.codigo
            else:
                lotepartida = 'VACIO'
            producto = parte.articulos != [] and parte.articulos[0].productoVenta.nombre or 'VACÍO'
            model[iter][-2] = lotepartida

    def calcular_duracion(self, hfin, hini):
        """
        DEPRECATED.
        ¡OBSOLETO!
        """
        if isinstance(hfin, mx.DateTime.DateTimeDeltaType):
            hfin = hfin + mx.DateTime.oneDay 
        duracion = hfin - hini
        if duracion.day > 0:
            duracion -= mx.DateTime.oneDay
        return duracion
    
    def rellenar_agujas(self):
        """ DEPRECATED """
        #model = self.wids['tv_agujas'].get_model()
        #model.clear()
        #cantidad = 0
        #for consumo in [c for c in self.objeto.consumos if c.antes == -3 and c.despues == -3]:
        #    model.append((consumo.productoCompra.descripcion, int(consumo.cantidad), consumo.id))
        #    cantidad += consumo.cantidad
        #self.wids['e_total_agujas'].set_text(utils.float2str(cantidad, 0))
        pass
        
    def rellenar_widgets(self):
        """
        Introduce la información del partedeproduccion actual
        en los widgets.
        No se chequea que sea != None, así que
        hay que tener cuidado de no llamar a 
        esta función en ese caso.
        """
        self.wids['sp_merma'].set_value(self.objeto.merma * 100)
        # Added 4/6/2006. Consumo de plástico alternativo:
        self.wids['e_plastico'].set_text(
            self.plastico and self.plastico.descripcion or "SIN ENVOLVER")
        # DONE: BUG: Creo que aquí. Al darle a NUEVO no se borra la información del lote y artículo del parte anterior.
        #  (Sospecho que lo del artículo es por no poner self.articulo = None y el lote ¿por no borrar el e_lote?)
        # It's not a bug, it's a feature!
        # NOTA: De momento se deja así (es en nuevo_ donde se debería poner el artículo a None y demás) a petición
        # del usuario -le parece más cómodo que se inicie con el mismo lote y artículo del parte anterior en pantalla-.
        # Si cambia el requerimiento (que cambiará) ya sabes dónde tienes que tocar, gañanazo.
        partedeproduccion = self.objeto
        self.wids['ch_bloqueado'].set_active(self.objeto.bloqueado)
        # Información global:
        self.wids['e_fecha'].set_text(utils.str_fecha(partedeproduccion.fecha))
        self.wids['e_hora_ini'].set_text(partedeproduccion.horainicio.strftime('%H:%M'))
        self.wids['e_hora_fin'].set_text(partedeproduccion.horafin.strftime('%H:%M'))
        self.wids['e_o11'].set_text(str(partedeproduccion.prodestandar))
        self.wids['e_tiempo_total'].set_text(partedeproduccion.get_duracion().strftime('%H:%M'))
        self.wids['txt_observaciones'].get_buffer().set_text(partedeproduccion.observaciones)
        # Ya no se usa y además protesta: 
        # /home/queen/Q-INN/geotexan/geotexinn02/formularios/partes_
        #   de_fabricacion_rollos.py:782: Warning: g_signal_emit_valist: 
        #   assertion `signal_id > 0' failed
        #self.wids['sp_merma'].set_value(partedeproduccion.merma * 100)
        # Información de detalle:
        if self.objeto.articulos != []:
            self.producto = self.objeto.articulos[0].productoVenta
        self.rellenar_datos_articulo(self.producto)
        self.wids['e_fichaproduccion'].set_text(partedeproduccion.fichaproduccion)
        self.rellenar_tabla_empleados()
        for a in self.objeto.articulos:
            try:
                self.wids['e_partida_gtx'].set_text(a.partida.codigo)
                self.wids['e_partida'].set_text(a.partida.partidaCarga.codigo)
                break
            except:
                self.wids['e_partida_gtx'].set_text("")
                self.wids['e_partida'].set_text('')
        self.rellenar_tabla_rollos()
        self.rellenar_balas()
        self.rellenar_agujas()
        self.rellenar_tabla_consumos()
        self.rellenar_tabla_desechos()
        self.objeto.make_swap()
        self.check_permisos()
    
    def rellenar_tabla_desechos(self):
        """
        Rellena la tabla de desechos del parte.
        """
        parte = self.objeto
        if parte != None:
            model = self.wids['tv_desecho'].get_model()
            self.wids['tv_desecho'].set_model(None)
            model.clear()
            desechos = parte.descuentosDeMaterial[:]
            try:
                desechos.sort(lambda c1, c2: c1 != None and c2 != None and int(c1.id - c2.id) or 0)
            except TypeError, msg:
                self.logger.error("partes_de_fabricacion_rollos.py (rellenar_tabla_desechos): Error ordenando descuento de material (%s):\n%s" % (msg, desechos))
            for c in desechos:
                if c.productoCompraID != None:
                    unidad = c.productoCompra.unidad
                    producto = c.productoCompra.descripcion
                else:
                    unidad = ""
                    producto = ""
                model.append((producto, 
                              "%s %s" % (utils.float2str(c.cantidad), unidad), 
                              c.observaciones,
                              c.id))
            self.wids['tv_desecho'].set_model(model)

    def rellenar_tabla_consumos(self):
        """
        Rellena la tabla de consumos del parte.
        """
        parte = self.objeto
        if parte != None:
            model = self.wids['tv_consumos'].get_model()
            self.wids['tv_consumos'].set_model(None)
            model.clear()
            consumos = parte.consumos[:]
            try:
                consumos.sort(lambda c1, c2: c1 != None and c2 != None and int(c1.id - c2.id) or 0)
            except TypeError, msg:
                self.logger.error("partes_de_fabricacion_rollos.py (rellenar_tabla_consumos): Error ordenando consumos (%s):\n%s" % (msg, consumos))
            for c in parte.consumos:
                if c.productoCompraID != None:
                    unidad = c.productoCompra.unidad
                    producto = c.productoCompra.descripcion
                else:
                    unidad = ""
                    producto = ""
                model.append((producto, 
                              "%s %s" % (utils.float2str(c.cantidad), unidad), 
                              c.id))
            self.wids['tv_consumos'].set_model(model)

    def check_permisos(self):
        if "w" in self.__permisos:  # Puede modificar los partes:
            self.activar_widgets(True)
        else:   # Sólo puede modificar el parte que haya creado nuevo (si es que ha creado alguno)
            if self.__lecturaescritura == self.objeto.id or not self.objeto.bloqueado:
                self.activar_widgets(True)
            else:
                self.activar_widgets(False)
        # Compruebo primero este porque habilita o deshabilita todos los botones, incluso los que 
        # dependen de los otros dos permisos.
        if "r" in self.__permisos:  # Puede leer partes anteriores, habilito el buscar:
            self.wids['b_buscar'].set_sensitive(True)
        else:
            self.wids['b_buscar'].set_sensitive(False)
        if "x" in self.__permisos:  # Puede crear nuevos:
            self.wids['b_nuevo'].set_sensitive(True)
        else:
            self.wids['b_nuevo'].set_sensitive(False)
            
    def colorear_pesos(self):
        """
        Cambia el color de e_consumo_estimado y e_consumo_real
        dependiendo de si se ha consumido más de lo estimado o menos.
        """
        try:
            real = float(self.wids['e_consumo_real'].get_text())
        except:
            real = 0
        try:
            #balas = float(self.wids['e_total_balas'].get_text())
            balas = sum([b.pesobala for b in self.get_partida().balas]) 
                # Si se llama a get_partida antes que a rellenar_rollos no devuelve la partida correcta.
        except:
            balas = 0
        try:
            estimado = float(self.wids['e_consumo_estimado'].get_text())
        except:
            estimado = 0
        # DEBUG: print "balas", balas, "estimado", estimado, "real", real
        if balas < estimado:
            self.wids['e_consumo_estimado'].modify_base(gtk.STATE_NORMAL, self.wids['e_consumo_estimado'].get_colormap().alloc_color("red"))
        else:
            self.wids['e_consumo_estimado'].modify_base(gtk.STATE_NORMAL, self.wids['e_consumo_estimado'].get_colormap().alloc_color("white"))
        if balas < real:
            self.wids['e_consumo_real'].modify_base(gtk.STATE_NORMAL, self.wids['e_consumo_real'].get_colormap().alloc_color("red"))
        else:
            self.wids['e_consumo_real'].modify_base(gtk.STATE_NORMAL, self.wids['e_consumo_real'].get_colormap().alloc_color("white"))


    def cmpfechahora_or_numrollo(self, detalle1, detalle2):
        """
        Si tiene número de rollo, ordena por número de rollo. En otro caso,
        ordena por fecha y hora de fabricación/incidencia.
        """
        try:
            if detalle1.rollo.numrollo < detalle2.rollo.numrollo:
                return -1
            if detalle1.rollo.numrollo > detalle2.rollo.numrollo:
                return 1
            return 0
        except AttributeError:
            if detalle1.fechahora < detalle2.fechahora:
                return -1
            elif detalle1.fechahora > detalle2.fechahora:
                return 1
            else:
                return 0

    def partida(self, d):
        try:
            res = d.partida.codigo
        except AttributeError:
            res = ""
        return res

    def rollo(self, d):
        try:
            res = d.codigo
        except AttributeError:
            res = ''
        return res

    def peso(self, d):
        try:
            res = d.peso
        except AttributeError:
            res = 0.0
        return res

    def densidad(self, d):
        try:
            if d.es_rollo():
                res = d.rollo.densidad
            elif d.es_rollo_defectuoso():
                res = d.rolloDefectuoso.densidad
            else:
                res = 0.0
        except AttributeError:
            res = 0.0
        return res

    def longitud(self, d):
        try:
            res = d.largo
        except AttributeError:
            res = 0.0
        return res

    def ancho(self, d):
        try:
            res = d.ancho
        except AttributeError:
            res = 0.0
        return res

    def motivo(self, d):
        try:
            res = d.tipoDeIncidencia.descripcion
        except AttributeError:
            if d.es_rollo_defectuoso():
                res = "%s m lineales" % (utils.float2str(d.largo, 1))
            else:
                res = ''
        return res

    def horaini(self, d):
        try:
            res = d.horainicio.strftime('%H:%M')
        except AttributeError:
            res = ''
        return res

    def horafin(self, d):
        try:
            res = d.horafin.strftime('%H:%M')
        except AttributeError:
            res = ''
        return res

    def duracion(self, d):
        try:
            duracion = (d.horafin - d.horainicio)
            try:
                res = duracion.strftime('%H:%M')
            except AttributeError:
                res = "%d:%02d" % (duracion.seconds / 3600, 
                                   duracion.seconds / 60 % 60)
        except AttributeError:
            res = ''
        return res

    def observaciones(self, d):
        try:
            res = d.observaciones
        except AttributeError:
            if d.es_rollo():
                res = d.rollo.observaciones
            elif d.es_rollo_defectuoso():
                res = d.rolloDefectuoso.observaciones
            else:
                res = ""
        return res

    def calcular_tiempo_trabajado(self, parte):
        tiempototal = parte.get_duracion()
        paradas = [p for p in parte.incidencias]
        tiempoparadas = 0
        for parada in paradas:
            tiempoparadas += parada.get_duracion()
        return tiempototal, tiempototal - tiempoparadas

    def convertir_densidad_a_float(self, text, regexp):
        lista_digitos = regexp.findall(text)
        lista_digitos = [i for i in lista_digitos if i != '']
        if lista_digitos == []:
            return None
        else:
            try:
                return float(".".join(lista_digitos))
            except ValueError:
                return None

    def cargar_imagen(self, w, imagen):
        """
        Carga la imagen "imagen" del directorio "imagenes" en el widget.
        """
        im = os.path.join('..', 'imagenes', imagen)
        w.set_from_file(im)

    def mostrar_icono(self, densidad_anterior, densidad_actual):
        """
        Muestra un icono que indica si la densidad media ha subido, bajado, etc...
        """
        if densidad_anterior == None or densidad_actual == None:
            self.cargar_imagen(self.wids['im_dm'], 'none.png')
        else:
            densidad_actual = round(densidad_actual, 1)
            if densidad_anterior < densidad_actual:
                if (densidad_anterior * 1.1) >= densidad_actual:
                    self.cargar_imagen(self.wids['im_dm'], 'up_right.png')
                else:
                    self.cargar_imagen(self.wids['im_dm'], 'up.png')
            elif densidad_anterior > densidad_actual:
                if (densidad_anterior * 0.9) <= densidad_actual:
                    self.cargar_imagen(self.wids['im_dm'], 'down_right.png')
                else:
                    self.cargar_imagen(self.wids['im_dm'], 'down.png')
            else:
                self.cargar_imagen(self.wids['im_dm'], 'right.png')

    def mostrar_densidad_media(self, densidades):
        """
        Muestra la densidad media y el icono de evolución.
        """
        regexp = re.compile("\d*")
        try:
            densidad_anterior = self.convertir_densidad_a_float(self.wids['e_densidad_media'].get_text(), regexp)
            densidad_media = sum(densidades) / len(densidades)
            self.wids['e_densidad_media'].set_text("%s gr/m²" % (utils.float2str(densidad_media, 1)))
        except ZeroDivisionError:
            densidad_media = None
            self.wids['e_densidad_media'].set_text("-")
        self.mostrar_icono(densidad_anterior, densidad_media)
  

    def rellenar_tabla_rollos(self, actualizar_tabla = True):
        """
        Si actualizar_tabla es False no toca el model; aunque 
        sí que actualiza los datos del pie de tabla.
        """
        model = self.wids['tv_rollos'].get_model()
        if actualizar_tabla:
            model.clear()
        detallesdeproduccion = ([i for i in self.objeto.incidencias] 
                                + [a for a in self.objeto.articulos])
        detallesdeproduccion.sort(self.cmpfechahora_or_numrollo)
        pesototal = 0
        # densidades = []
        # Filas del TreeView
        for detalle in detallesdeproduccion:
            # densidades.append(self.densidad(detalle))
            if actualizar_tabla:
                model.append((self.partida(detalle),
                              self.rollo(detalle),
                              self.peso(detalle),
                              self.densidad(detalle),
                              self.motivo(detalle),
                              self.horaini(detalle),
                              self.horafin(detalle),
                              self.duracion(detalle),
                              self.observaciones(detalle),
                              detalle.id))
            pesototal += self.peso(detalle)
        # Campos del pie de la tabla:
        # self.mostrar_densidad_media(densidades)
        self.wids['e_consumo_real'].set_text('%s' % (
            utils.float2str(round(pesototal, 2))))
        rollos = [d for d in self.objeto.articulos]
        self.wids['e_num_rollos'].set_text(str(len(rollos)))
        metros = sum([r.largo for r in rollos])
        self.wids['e_metros_lineales'].set_text(utils.float2str(metros, 0))
        partedeproduccion = self.objeto
        tiempototal, tiemporeal = self.calcular_tiempo_trabajado(
                                    partedeproduccion)
        self.wids['e_tiempo_real_trabajado'].set_text(
            tiemporeal.strftime('%H:%M'))
        try:
            productividad = (tiemporeal.seconds / tiempototal.seconds) * 100
        except ZeroDivisionError:
            productividad = 100
        self.wids['e_productividad'].set_text("%s %%" % (
            utils.float2str(productividad)))
        if self.producto != None:
            peso_total = (metros * self.producto.camposEspecificosRollo.ancho
                          * self.producto.camposEspecificosRollo.gramos / 1000)
        else:
            peso_total = 0
        self.wids['e_peso_total'].set_text("%s" % utils.float2str(peso_total))
            # Peso total teórico, SIN embalajes.
        merma = self.wids['sp_merma'].get_value() / 100.0     # (está en % 
                                                              # como entero)
        consumo_estimado = peso_total / (1.0 - merma)
        self.wids['e_consumo_estimado'].set_text("%s" % (
            utils.float2str(consumo_estimado)))
        rendimiento = self.objeto.calcular_rendimiento()
        self.wids['e_rendimiento'].set_text("%s %%" % (
            utils.float2str(rendimiento)))
        iter_ant = model.get_iter_first()
        if iter_ant != None:
            iter_post = model.iter_next(iter_ant)
        else:
            iter_post = None
        while iter_post != None:
            iter_ant = iter_post
            iter_post = model.iter_next(iter_ant)
        if iter_ant != None:
            path_siguiente = model.get_path(iter_ant)
            sel = self.wids['tv_rollos'].get_selection()
            sel.select_iter(iter_ant)
            self.wids['tv_rollos'].scroll_to_cell(path_siguiente, 
                                                  use_align = True)
            column = self.wids['tv_rollos'].get_column(2)
            cell = column.get_cell_renderers()[0]
            self.wids['tv_rollos'].set_cursor_on_cell(path_siguiente, 
                                                      column, 
                                                      cell, 
                                                      start_editing = False)
        self.mostrar_densidad_media([a.rollo.densidad 
                                     for a in self.objeto.articulos 
                                     if a.rollo != None])   
            # OJO: La densidad media no tiene en cuenta los rollos defectuosos.
        self.rellenar_pie_rollos_ab()
        self.colorear_pesos()

    def rellenar_pie_rollos_ab(self):
        """
        Recuenta e introduce en el pie del parte los 
        totales de rollos A y B (alias "defectuosos").
        """
        pesoa = pesob = 0.0
        peso_sina = peso_sinb = 0.0
        metrosa = metrosb = 0.0
        numrollosa = numrollosb = 0
        mlina = mlinb = 0.0
        pesoEmbalaje = None
        metrosLineales = None
        metrosCuadrados = None
        for a in self.objeto.articulos:
            if a.es_rollo_defectuoso():
                numrollosb += 1
                pesob += a.peso
                peso_sinb += a.peso_sin
                metrosb += a.superficie
                mlinb += a.largo
            elif a.es_rollo():
                if pesoEmbalaje == None:
                    pesoEmbalaje = a.rollo.productoVenta.camposEspecificosRollo.pesoEmbalaje
                if metrosLineales == None:
                    metrosLineales = a.rollo.productoVenta.camposEspecificosRollo.metrosLineales
                if metrosCuadrados == None:
                    metrosCuadrados = a.rollo.productoVenta.camposEspecificosRollo.metros_cuadrados
                numrollosa += 1
                apeso = a.peso
                #pesoa += a.peso
                pesoa += apeso
                #peso_sina += a.peso_sin
                peso_sina += apeso - pesoEmbalaje
                #metrosa += a.superficie
                #mlina += a.largo
            else:
                self.logger.error("partes_de_fabricacion_rollos::rellenar_pie_rollos_ab -> ¡Artículo ID %d no es rollo ni rollo defectuoso!" % (a.id))
        if metrosLineales != None:
            mlina = metrosLineales * numrollosa
        if metrosCuadrados != None:
            metrosa = metrosCuadrados * numrollosa
        self.wids['e_num_a'].set_text(`numrollosa`)
        self.wids['e_num_b'].set_text(`numrollosb`)
        self.wids['e_peso_a'].set_text(utils.float2str(pesoa))
        self.wids['e_peso_b'].set_text(utils.float2str(pesob))
        self.wids['e_peso_sin_a'].set_text(utils.float2str(peso_sina))
        self.wids['e_peso_sin_b'].set_text(utils.float2str(peso_sinb))
        self.wids['e_metros_a'].set_text(utils.float2str(metrosa, 1))
        self.wids['e_metros_b'].set_text(utils.float2str(metrosb, 1))
        self.wids['e_mlin_a'].set_text(utils.float2str(mlina, 1))
        self.wids['e_mlin_b'].set_text(utils.float2str(mlinb, 1))


    def actualizar_consumo_estimado(self, sp):
        if self.producto != None:
            rollos = [d for d in self.objeto.articulos]
            metros = sum([r.productoVenta.camposEspecificosRollo.metrosLineales for r in rollos])
            peso_total = metros*self.producto.camposEspecificosRollo.ancho*self.producto.camposEspecificosRollo.gramos/1000
            merma = self.wids['sp_merma'].get_value() / 100.0     # (está en % como entero)
            consumo_estimado = peso_total / (1.0 - merma)
            self.wids['e_consumo_estimado'].set_text("%sf" % (utils.float2str(consumo_estimado)))
            self.colorear_pesos()
        return False    # Porque further processing is required. I suppose.

    def rellenar_datos_articulo(self, producto):
        """
        A partir del artículo recibido, completa la información
        de la cabecera del formulario (ancho, etc...) en 
        función de los datos de la rollo.
        También verifica si el parte tiene ficha de fabricación. Si no la 
        tiene, pone la del producto recibido.
        """
        if producto == None:
            self.wids['e_articulo'].set_text('')
            self.wids['e_grsm2'].set_text('')
            self.wids['e_ancho'].set_text('')
            self.wids['e_long_rollo'].set_text('')
        else:
            self.wids['e_articulo'].set_text(producto.nombre)
            ce = producto.camposEspecificosRollo
            self.wids['e_grsm2'].set_text(ce and str(ce.gramos) or '')
            self.wids['e_ancho'].set_text(ce and str(ce.ancho) or '')
            self.wids['e_long_rollo'].set_text(ce and str(ce.metrosLineales) or '')
            if not self.objeto.fichaproduccion:
                self.objeto.fichaproduccion = ce.fichaFabricacion

    # --------------- Manejadores de eventos ----------------------------
    def cambiar_peso_rollo(self, cell, path, newtext):
        model = self.wids['tv_rollos'].get_model()
        if model[path][1] == '':	# Nº rollo, no tiene, no es un rollo.
            return
        id = model[path][-1]
        articulo = pclases.Articulo.get(id)
        if articulo.es_rollo():
            rollo = articulo.rollo
        elif articulo.es_rollo_defectuoso():
            rollo = articulo.rolloDefectuoso
        try:
            descontar_material_adicional(self, rollo.articulo, restar = False)
            rollo.peso = float(newtext)
        except ValueError:
            utils.dialogo_info('NÚMERO INCORRECTO', 'El peso del rollo debe ser un número.', padre = self.wids['ventana'])
            return
        descontar_material_adicional(self, rollo.articulo, restar = True)
        model[path][2] = rollo.peso     # Columna 2 = peso. Columna 3 = densidad.
        if articulo.es_rollo():
            pesosin = (rollo.peso - articulo.productoVenta.camposEspecificosRollo.pesoEmbalaje) * 1000
        elif articulo.es_rollo_defectuoso():
            pesosin = (rollo.peso - rollo.pesoEmbalaje) * 1000
        try:
            dens = pesosin / (articulo.superficie)
        except ZeroDivisionError:
            dens = 0
        rollo.densidad = dens 
        model[path][3] = rollo.densidad
        self.rellenar_tabla_rollos(actualizar_tabla = False)
        iter = model.get_iter(path)
        iter = model.iter_next(iter)
        if iter != None:
            path_siguiente = model.get_path(iter)
            column = self.wids['tv_rollos'].get_column(2)
            cell = column.get_cell_renderers()[0]
            self.wids['tv_rollos'].set_cursor_on_cell(path_siguiente, column, cell, start_editing=False)

    def cambiar_motivo_incidencia(self, cell, path, newtext):
        # Funcionalidad no implementada.
        pass

    def cambiar_observaciones(self, cell, path, newtext):
        model = self.wids['tv_rollos'].get_model()
        id = model[path][-1]
        if model[path][1] != '':	# Nº rollo, tiene, no es una incidencia.
            articulo = pclases.Articulo.get(id)
            if articulo.es_rollo():
                rollo = articulo.rollo
            elif articulo.es_rollo_defectuoso():
                rollo = articulo.rolloDefectuoso
            rollo.observaciones = newtext
        else:
            incidencia = pclases.Incidencia.get(id)
            incidencia.observaciones = newtext
        model[path][-2] = newtext

    def cambiar_inicio_incidencia(self, cell, path, newtext):
        model = self.wids['tv_rollos'].get_model()
        if model[path][1] != '':	# Nº rollo, tiene, no es una incidencia.
            return
        id = model[path][-1]
        incidencia = pclases.Incidencia.get(id)
        try:
            incidencia.horainicio = mx.DateTime.DateTimeFrom(
                                        day = self.objeto.fecha.day, 
                                        month = self.objeto.fecha.month, 
                                        year = self.objeto.fecha.year, 
                                        hour = int(newtext.split(":")[0]), 
                                        minute = int(newtext.split(":")[1]))
            if (incidencia.horafin - incidencia.horainicio).days > 1:
                incidencia.horainicio + mx.DateTime.oneDay
            while incidencia.horainicio < self.objeto.fechahorainicio: 
                    # El parte está en la franja de medianoche y la 
                    # incidencia comienza después de las 12.
                horaini += mx.DateTime.oneDay   # Debe llevar la fecha del 
                                                # día siguiente.
                horafin += mx.DateTime.oneDay
        except (ValueError, IndexError):
            utils.dialogo_info('HORA INCORRECTA', 
                'La fecha y hora deben respetar el formato inicial.\nSe va '
                'a reestablecer el valor antiguo,\na continuación trate de '
                'editar este valor conservando su formato.', 
                padre = self.wids['ventana'])
            return
        self.rellenar_tabla_rollos()

    def cambiar_fin_incidencia(self, cell, path, newtext):
        model = self.wids['tv_rollos'].get_model()
        if model[path][1] != '':	# Nº rollo, tiene, no es una incidencia.
            return
        id = model[path][-1]
        incidencia = pclases.Incidencia.get(id)
        try:
            incidencia.horafin = mx.DateTime.DateTimeFrom(
                                        day = self.objeto.fecha.day, 
                                        month = self.objeto.fecha.month, 
                                        year = self.objeto.fecha.year, 
                                        hour = int(newtext.split(":")[0]), 
                                        minute = int(newtext.split(":")[1]))
            if (incidencia.horafin - incidencia.horainicio).days < 0:
                incidencia.horafin += mx.DateTime.oneDay
            while incidencia.horainicio < self.objeto.fechahorainicio: 
                    # El parte está en la franja de medianoche y la incidencia 
                    # comienza después de las 12.
                horaini += mx.DateTime.oneDay   # Debe llevar la fecha del 
                                                # día siguiente.
                horafin += mx.DateTime.oneDay
        except (ValueError, IndexError):
            utils.dialogo_info('HORA INCORRECTA', 
                'La fecha y hora deben respetar el formato inicial.\nSe va a'
                ' reestablecer el valor antiguo,\na continuación trate de '
                'editar este valor conservando su formato.', 
                padre = self.wids['ventana'])
            return
        self.rellenar_tabla_rollos()

    def crear_nuevo_partedeproduccion(self, widget):
        """
        Función callback del botón b_nuevo.
        Pide los datos básicos para crear un nuevo objeto.
        Una vez insertado en la BD hay que hacerlo activo
        en la ventana para que puedan ser editados el resto
        de campos que no se hayan pedido aquí.
        """
        self.ultima_etiqueta = None
        partedeproduccion = self.objeto
            # Datos a pedir: Ninguno. Lo planto todo con valores por defecto y listo.
        if not utils.dialogo('Se creará un nuevo parte de producción vacío.', 
                             'NUEVO PARTE', 
                             padre = self.wids['ventana']): 
            return
        if partedeproduccion != None:
            partedeproduccion.notificador.desactivar()
        partedeproduccion = pclases.ParteDeProduccion(fecha = time.localtime(),
            horainicio = time.struct_time(time.localtime()[:4] 
                                          + (0,0) 
                                          + time.localtime()[6:]),
            horafin = time.struct_time(time.localtime()[:3]
                                       +((time.localtime()[3]+8)%24, 0,0)
                                       +time.localtime()[6:]),
            prodestandar = 0,
            observaciones = '',
            bloqueado = False)
        partedeproduccion._corregir_campos_fechahora()
        self.objeto = partedeproduccion
        self.wids['e_partida'].set_text('')
        self.wids['e_partida_gtx'].set_text('')
        self.wids['e_fichaproduccion'].set_text('')
        self.add_empleados_calendario()
        self.__lecturaescritura = self.objeto.id
        self.actualizar_ventana()
        self.objeto.notificador.activar(self.aviso_actualizacion)
        verificar_solapamiento(partedeproduccion, self.wids['ventana'])

    def refinar_resultados_busqueda_producto(self, resultados):
        """
        Muestra en una ventana de resultados todos los
        registros de "resultados".
        Devuelve el id (primera columna de la ventana
        de resultados) de la fila seleccionada o None
        si se canceló.
        """
        filas_res = []
        for r in resultados:
            filas_res.append((r.id, r.codigo, r.nombre, r.descripcion))
        idproducto = utils.dialogo_resultado(filas_res,
                                             titulo = 'Seleccione producto',
                                             cabeceras = ('ID Interno', 'Código','Nombre', 'Descripción'), 
                                             padre = self.wids['ventana'])
        if idproducto < 0:
            return None
        else:
            return idproducto

    def buscar_partedeproduccion(self, widget):
        """
        Muestra una ventana de búsqueda y a continuación los
        resultados. El objeto seleccionado se hará activo
        en la ventana a no ser que se pulse en Cancelar en
        la ventana de resultados.
        """
        partedeproduccion = self.objeto
        a_buscar = utils.dialogo_entrada(titulo = "BUSCAR PARTE", 
            texto = "Introduzca fecha del parte o nombre del producto:", 
            padre = self.wids['ventana'])
        if a_buscar != None:
            try:
                if a_buscar != '':
                    a_buscar = a_buscar.replace("-", "/")
                    if a_buscar.count('/') == 1:
                        a_buscar = "%s/%d" % (a_buscar, mx.DateTime.localtime().year)
                    if len(a_buscar.split('/')[-1]) == 2:
                        fecha = time.strptime(a_buscar, '%d/%m/%y')
                    else:
                        fecha = time.strptime(a_buscar, '%d/%m/%Y')
                    resultados = pclases.ParteDeProduccion.select(pclases.ParteDeProduccion.q.fecha == fecha)
                    resultados = [r for r in resultados if r.es_de_geotextiles()] 
                else:
                    resultados = pclases.ParteDeProduccion.select("""NOT observaciones LIKE '%;%;%;%;%;%'""")
            except:
                producto = pclases.ProductoVenta.select(pclases.AND(pclases.ProductoVenta.q.nombre.contains(a_buscar), 
                                                                    pclases.ProductoVenta.q.camposEspecificosRolloID != None))
                resultados = pclases.ParteDeProduccion.select()
                # Pongo la barra porque con muchos partes esto tarda
                vpro = VentanaProgreso(padre = self.wids['ventana'])
                vpro.mostrar()
                i = 0.0
                tot = resultados.count()
                partes = []
                if producto.count() > 1:
                    idproducto = self.refinar_resultados_busqueda_producto(producto)
                    if idproducto != None:
                        for p in resultados:
                            if p.articulos != [] and p.articulos[0].productoVentaID == idproducto:
                                partes.append(p)
                            vpro.set_valor(i/tot, 'Buscando partes')
                            i += 1
                    else:
                        vpro.ocultar()
                        return
                elif producto.count() == 1:
                    for p in resultados:
                        if p.articulos != [] and p.articulos[0].productoVentaID == producto[0].id:
                            partes.append(p)
                        vpro.set_valor(i/tot, 'Buscando partes')
                        i += 1
                else:
                    for p in resultados:
                        if p.es_de_geotextiles():
                            partes.append(p)
                        vpro.set_valor(i/tot, 'Buscando partes')
                        i += 1
                vpro.ocultar()
                resultados = partes
            # NOTA: Ver ir_a_primero para comprender el criterio de seleccion.
            # OJO: Se usa en dos partes del código: refactorizar y crear una funcioncita por si hay que cambiarlo en el futuro.
            try:
                len_resultados = len(resultados)
            except:
                len_resultados = resultados.count()
            if len_resultados > 1:
                ## Refinar los resultados
                idpartedeproduccion = self.refinar_resultados_busqueda(resultados)
                if idpartedeproduccion == None:
                    return
                resultados = [pclases.ParteDeProduccion.get(idpartedeproduccion)]
                # Se supone que la comprensión de listas es más rápida que hacer un nuevo get a SQLObject.
                # Me quedo con una lista de resultados de un único objeto ocupando la primera posición.
                # (Más abajo será cuando se cambie realmente el objeto actual por este resultado.)
            elif len_resultados < 1:
                ## Sin resultados de búsqueda
                utils.dialogo_info('SIN RESULTADOS', 'La búsqueda no produjo resultados.\nPruebe a cambiar el texto buscado o déjelo en blanco para ver una lista completa.\n(Atención: Ver la lista completa puede resultar lento si el número de elementos es muy alto)', padre = self.wids['ventana'])
                return
            ## Un único resultado
            # Primero anulo la función de actualización
            if partedeproduccion != None:
                partedeproduccion.notificador.desactivar()
            # Pongo el objeto como actual
            try:
                partedeproduccion = resultados[0]
            except IndexError:
                utils.dialogo_info(titulo = "ERROR", 
                                   texto = "Se produjo un error al recuperar la información.\nCierre y vuelva a abrir la aplicación antes de volver a intentarlo.", 
                                   padre = self.wids['ventana'])
                return
            # Y activo la función de notificación:
            partedeproduccion.notificador.activar(self.aviso_actualizacion)
            self.objeto = partedeproduccion
            self.actualizar_ventana()

    def guardar(self, widget):
        """
        Guarda el contenido de los entry y demás widgets de entrada
        de datos en el objeto y lo sincroniza con la BD.
        """
        partedeproduccion = self.objeto
        ye_olde_fecha, ye_olde_horainicio, ye_olde_horafin = partedeproduccion.fecha, partedeproduccion.horainicio, partedeproduccion.horafin
        ye_olde_horainicio = utils.str_hora_corta(partedeproduccion.horainicio) 
        ye_olde_horafin = utils.str_hora_corta(partedeproduccion.horafin)
            # Campos del objeto que hay que guardar:
        # Fecha, horainicio, horafin, prodestandar y observaciones con el formateado especial.
        fecha = self.wids['e_fecha'].get_text()
        horainicio = self.wids['e_hora_ini'].get_text()
        horafin = self.wids['e_hora_fin'].get_text()
        prodestandar = self.wids['e_o11'].get_text()
        try:
            prodestandar = float(prodestandar)
        except:
            prodestandar = 0
        if prodestandar != 0 and self.producto != None and self.producto.prodestandar == 0:
            self.producto.prodestandar = prodestandar
        bounds = self.wids['txt_observaciones'].get_buffer().get_bounds()
        observaciones = self.wids['txt_observaciones'].get_buffer().get_text(bounds[0], bounds[1])
        # Desactivo el notificador momentáneamente
        partedeproduccion.notificador.activar(lambda: None)
        # Actualizo los datos del objeto
        partedeproduccion.prodestandar = prodestandar
        partedeproduccion.observaciones = observaciones
        partedeproduccion.fichaproduccion = self.wids['e_fichaproduccion'].get_text()
        partedeproduccion.merma = self.wids['sp_merma'].get_value() / 100.0
        try:
            partedeproduccion.fecha = utils.parse_fecha(fecha)
        except:
            partedeproduccion.fecha = time.localtime()
        partedeproduccion.horainicio = horainicio
        partedeproduccion.horafin = horafin
        partedeproduccion._corregir_campos_fechahora()
        # Verificación de que no se solapa con otros partes:
        verificar_solapamiento(partedeproduccion, 
                               self.wids['ventana'], 
                               ye_olde_fecha, 
                               ye_olde_horainicio, 
                               ye_olde_horafin)
        # Fuerzo la actualización de la BD y no espero a que SQLObject lo haga 
        # por mí:
        partedeproduccion.sync()
        # Vuelvo a activar el notificador
        partedeproduccion.notificador.activar(self.aviso_actualizacion)
        self.actualizar_ventana()
        self.wids['b_guardar'].set_sensitive(False)

    def borrar_parte(self, boton):
        if not utils.dialogo('Se va a intentar eliminar el parte actual.\nSi hay operaciones complejas implicadas se cancelará el borrado.\nDe cualquier forma, no se aconseja eliminar ningún parte que ya tenga rollos relacionadas.\n¿Está seguro de borrar el parte actual?', 'ELIMINAR PARTE', padre = self.wids['ventana']): return
        partedeproduccion = self.objeto
        partedeproduccion.notificador.desactivar()
        try:
            partedeproduccion.destroySelf()
        except:
            utils.dialogo_info('PARTE NO BORRADO', 'El parte no se eliminó.\nSi tiene rollos o empleados asociados, trate primero de eliminarlos y vuelva a intentarlo.', padre = self.wids['ventana'])
            return
        self.ir_a_primero()

    def mostrar_calendario(self, boton):
        self.wids['e_fecha'].set_text(utils.str_fecha(utils.mostrar_calendario(fecha_defecto = self.objeto and self.objeto.fecha or None, padre = self.wids['ventana'])))
        self.guardar(None)
        self.add_empleados_calendario()
        self.rellenar_tabla_empleados()
    
    def set_hora_inicial(self, boton):
        valor_hora_ini = self.wids['e_hora_ini'].get_text()
        try:
            valor_hora_ini = [int(v) for v in valor_hora_ini.split(':')] + [0]
        except:
            valor_hora_ini = [0,0,0]
        hora_ini = utils.mostrar_hora(valor_hora_ini[0], valor_hora_ini[1], valor_hora_ini[2], 'HORA INICIO PARTE')
        # DONE: Hay que mostrar el título de hora inicial y hora final en la ventana.
        if hora_ini != None:
            partedeproduccion = self.objeto
            partedeproduccion.notificador.desactivar()
            partedeproduccion.horainicio = hora_ini
            partedeproduccion._corregir_campos_fechahora()
            self.set_hora_final(boton)  # Ahí se cambiarán los empleados si es preciso.
            self.actualizar_ventana()
            partedeproduccion.notificador.activar(self.aviso_actualizacion)
            verificar_solapamiento(partedeproduccion, self.wids['ventana'])

    def set_hora_final(self, boton):
        valor_hora_fin = self.wids['e_hora_fin'].get_text()
        try:
            valor_hora_fin = [int(v) for v in valor_hora_fin.split(':')] + [0]  # Porque el entry tiene solo H:M
        except:
            valor_hora_fin = [0,0,0]
        hora_fin = utils.mostrar_hora(valor_hora_fin[0], valor_hora_fin[1], valor_hora_fin[2], 'HORA FIN PARTE')
        if hora_fin != None:
            partedeproduccion = self.objeto
            partedeproduccion.notificador.desactivar()
            partedeproduccion.horafin = hora_fin
            partedeproduccion._corregir_campos_fechahora()
            partedeproduccion.syncUpdate()
            partedeproduccion.sync()
            self.add_empleados_calendario()
            self.actualizar_ventana()
            partedeproduccion.notificador.activar(self.aviso_actualizacion)
            verificar_solapamiento(partedeproduccion, self.wids['ventana'])

    def set_articulo(self, boton):
        """
        Muestra un cuadro de búsqueda de productos generados
        por la fábrica*. El seleccionado pasará a ser el 
        artículo del parte, mostrándose su información en la
        cabecera y limitando las opciones al añadir líneas.
        * Productos que sean rollos o tengan como línea de 
        producción la línea de fibra.
        """
        if self.objeto.articulos != []:
            txt = """
            Ya se ha iniciado la producción de un artículo. Si cambia el producto del parte actual              
            cambiará también en los rollos ya fabricados pertenecientes al parte.                               
            Si lo que desea es iniciar una nueva producción use el botón "Nuevo parte" y comience               
            un nuevo parte de producción. Si lo que quiere es cambiar el producto del parte actual              
            y todas sus rollos fabricados pulse "Sí".
            ¿Desea cambiar el producto fabricado en el parte?
            """
            if not utils.dialogo(titulo = '¿CAMBIAR LA PRODUCCIÓN?', 
                                 texto = txt, 
                                 padre = self.wids['ventana']):
                return 
        idlineasrollos = pclases.LineaDeProduccion.select(pclases.OR(
                pclases.LineaDeProduccion.q.nombre=='Línea de geotextiles', 
                pclases.LineaDeProduccion.q.nombre=='Línea de geocompuestos',
                pclases.LineaDeProduccion.q.nombre=='Línea de comercializados'))
            # OJO: Debe llamarse EXACTAMENTE Línea de xxxxxxxxxx en la BD.
        if idlineasrollos.count() == 0:
            # No hay línea de rollos
            utils.dialogo_info('ERROR LÍNEAS DE ROLLOS', 
                               'No hay líneas de geotextiles o geocompuestos/'
                               'comercializados en las bases de datos del '
                               'sistema.', 
                               padre = self.wids['ventana'])
            return 
        criterio = pclases.ProductoVenta.q.lineaDeProduccionID == idlineasrollos[0].id
        for i in xrange(1, idlineasrollos.count()):
            criterio = pclases.OR(criterio, pclases.ProductoVenta.q.lineaDeProduccionID == idlineasrollos[i].id)
        producto = self.buscar_producto(criterio)
        if producto != None:
            self.wids['e_o11'].set_text(utils.float2str(producto.prodestandar))
            self.wids['e_fichaproduccion'].set_text(
                producto.camposEspecificosRollo.fichaFabricacion)
            self.objeto.fichaproduccion \
                = self.wids['e_fichaproduccion'].get_text()
            self.guardar(None)
            self.producto = producto
            self.rellenar_datos_articulo(self.producto)
            for a in self.objeto.articulos:
                a.productoVenta = self.producto
        else:
            self.producto = None

    def buscar_producto(self, criterio_lineas):
        """
        Muestra una ventana de búsqueda y a continuación los
        resultados. El objeto seleccionado se hará activo
        en la ventana a no ser que se pulse en Cancelar en
        la ventana de resultados.
        """
        producto = self.producto
        a_buscar = utils.dialogo_entrada(titulo = "BUSCAR PRODUCTO", 
                                         texto = "Introduzca código, nombre o descripción de producto:", 
                                         padre = self.wids['ventana']) 
        if a_buscar != None:
            try:
                ida_buscar = int(a_buscar)
            except ValueError:
                ida_buscar = -1
            criterio = pclases.OR(pclases.ProductoVenta.q.codigo.contains(a_buscar),
                                    pclases.ProductoVenta.q.descripcion.contains(a_buscar),
                                    pclases.ProductoVenta.q.nombre.contains(a_buscar),
                                    pclases.ProductoVenta.q.id == ida_buscar)
            criterio = pclases.AND(criterio, criterio_lineas)
            resultados = pclases.ProductoVenta.select(criterio)
            if resultados.count() > 1:
                    ## Refinar los resultados
                    idproducto = self.refinar_resultados_busqueda_producto(resultados)
                    if idproducto == None:
                        return None
                    resultados = [pclases.ProductoVenta.get(idproducto)]
            elif resultados.count() < 1:
                    ## Sin resultados de búsqueda
                    utils.dialogo_info('SIN RESULTADOS', 'La búsqueda no produjo resultados.\nPruebe a cambiar el texto buscado o déjelo en blanco para ver una lista completa.\n(Atención: Ver la lista completa puede resultar lento si el número de elementos es muy alto)',
                                       padre = self.wids['ventana'])
                    return None
            ## Un único resultado
            # Primero anulo la función de actualización
            if producto != None:
                producto.notificador.desactivar()
            # Pongo el objeto como actual
            try:
                producto = resultados[0]
            except IndexError:
                utils.dialogo_info(titulo = "ERROR", 
                                   texto = "Se produjo un error al recuperar la información.\nCierre y vuelva a abrir la ventana antes de volver a intentarlo.", 
                                   padre = self.wids['ventana'])
                return None
        return producto

    def refinar_resultados_busqueda_producto(self, resultados):
        """
        Muestra en una ventana de resultados todos los
        registros de "resultados".
        Devuelve el id (primera columna de la ventana
        de resultados) de la fila seleccionada o None
        si se canceló.
        """
        filas_res = []
        for r in resultados:
            filas_res.append((r.id, r.codigo, r.nombre, r.descripcion))
        idproducto = utils.dialogo_resultado(filas_res,
                                             titulo = 'Seleccione producto',
                                             cabeceras = ('ID Interno', 'Código', 'Nombre', 'Descripción'), 
                                             padre = self.wids['ventana'])
        if idproducto < 0:
            return None
        else:
            return idproducto

    def add_rollo(self, boton):
        """
        Añade uno o varios rollos al parte de producción.
        Pide un número o rango de números de rollos e introduce
        un artículo y rollo correspondiente por cada uno de los
        códigos.
        1.- Chequear si self.producto != None
        2.- Chequear si hay número de partida en ventana.
        3.- Pedir número de rollos o rango de números de rollo.
        4.- Por cada número de rollo, hacer:
            4.1.- Crear rollo con código = str(numrollo)
            4.2.- Asociar rollo al partida.
            4.3.- Crear artículo relacionado con el rollo.
            4.4.- Relacionar artículo al parte (o hacerlo directamente al 
                  crear, claro).
            NEW! --> 4.5.- Descontar automáticamente el material adicional.
        """
        try:
            numpartida = self.wids['e_partida_gtx'].get_text().upper().replace("P-", "")
        except ValueError:
            utils.dialogo_info(titulo = 'PARTIDA ERRÓNEA', 
                               texto = 'El número de partida no es válido.', 
                               padre = self.wids['ventana'])
            return
        try:
            numpartida = int(numpartida)
            partida = pclases.Partida.select(
                pclases.Partida.q.numpartida == numpartida)[0]
        except IndexError:
            utils.dialogo_info(titulo = 'PARTIDA ERRÓNEA', 
                texto = 'La partida no se encontró.\nCree una partida nueva.', 
                padre = self.wids['ventana'])
            return
        except ValueError:
            utils.dialogo_info(titulo = 'PARTIDA ERRÓNEA', 
                texto = 'El número de partida %s no es válido.' % (numpartida),
                padre = self.wids['ventana'])
            return
        if self.producto == None:
            utils.dialogo_info(titulo = 'SELECCIONAR PRODUCTO', 
                texto = 'Seleccione primero el producto fabricado.', 
                padre = self.wids['ventana'])
            return
        if self.usuario == None or self.usuario.nivel > 3:
            self.iniciar_pesaje_auto(None)
        else:
            generador = self.pedir_rango()
            i = 0.0
            tot = len(generador)
            if tot > 500 and not utils.dialogo(titulo = "¿ESTÁ SEGURO?",
                                    texto = "Está intentando añadir más de "
                                            "500 rollos al parte.\n"
                                            "¿Está seguro?",
                                    padre = self.wids['ventana']):
                return
            vpro = VentanaProgreso(padre = self.wids['ventana'])
            vpro.mostrar()
            for numrollo in generador:
                if numrollo < 0:
                    numrollo *= -1
                    defectuoso = True
                else:
                    defectuoso = False
                try:
                    vpro.set_valor(i/tot, 'Añadiendo rollo nº %d...'%numrollo)
                    articulo = crear_articulo(numrollo, partida, 
                                              self.producto, self.objeto, 
                                              objeto_ventana_parte = self, 
                                              defectuoso = defectuoso)
                    if articulo != None:
                        vpro.set_valor(i/tot, '(%s) Descontando material...' % articulo.codigo)
                        descontar_material_adicional(self, articulo)
                        i += 1
                except psycopg_ProgrammingError:
                    vpro.ocultar()
                    utils.dialogo_info(titulo = 'ROLLO NO CREADO', 
                                       texto = 'El rollo no se pudo crear. Verifique que el número no esté duplicado.', 
                                       padre = self.wids['ventana'])
                    self.actualizar_ventana()
                    return
            vpro.ocultar()
            self.actualizar_ventana()

    def pedir_rango(self):
        """
        Pide un rango de números de rollos.
        Devuelve un generador de números
        de rollo que comienza en el primero 
        del rango (o único, si solo se teclea uno)
        y acaba en el último del rango.
        Si los números devueltos son negativos es porque
        había una "X" en el rango y hay que crearlos como 
        rollos defectuosos.
        """
        ultimo_mas_uno = pclases.Rollo._connection.queryOne("""SELECT ultimo_codigo_rollo_mas_uno(); """)[0]
        rango = utils.dialogo_entrada(titulo = 'INTRODUZCA RANGO',
                                      texto = 'Rango de números de rollos o el código indovidual.\nEscriba el rango de códigos de la forma "xxxx-yyyy", ambos inclusive.',
                                      padre = self.wids['ventana'],
                                      valor_por_defecto = ultimo_mas_uno)
        articulos = []
        if rango == '' or rango == None:
            return []
        rango = rango.upper()
        defectuosos = "X" in rango
        rango = rango.replace("R", "").replace("X", "")
        try:
            if '-' in rango:
                ini, fin = rango.split('-')
                ini = int(ini)
                fin = int(fin)
            else:
                ini = int(rango)
                fin = ini
        except:
            utils.dialogo_info(titulo = 'CÓDIGO INCORRECTO', texto = 'Los códigos deben ser numéricos.\n\nVerifique que los ha escrito correctamente y que ha separado el rango con un guión.', padre = self.wids['ventana'])
            return []
        if fin+1 - ini > 100:
            if not utils.dialogo(titulo = "¿ESTÁ SEGURO?",
                                 texto = "Ha introducido un rango demasiado grande (%s).\n¿Está realmente seguro de que quiere introducir %d artículos al parte?" % (rango, fin+1-ini), 
                                 padre = self.wids['ventana']):
                return xrange(0,0) 
        if not defectuosos:
            return xrange(ini, fin+1)
        else:
            return range(-fin, -ini + 1)[::-1]  # HACK: Python 2.3 no tiene __reversed__ en el xrange.
            
    def drop_rollo(self, boton):
        model, paths = self.wids['tv_rollos'].get_selection().get_selected_rows()
        if  paths == None or paths == []:
            utils.dialogo_info('ROLLO NO SELECCIONADO', 'Debe seleccionar el rollo que desee eliminar del parte.', padre = self.wids['ventana'])
            return
        if not utils.dialogo('¿Eliminar del parte?', 'BORRAR ROLLOS DE CONTROL DE PRODUCCIÓN', padre = self.wids['ventana']): 
            return
        for path in paths:
            id = model[path][-1]
            if model[path][1] == 0 or model[path][1] == "" or model[path][1] == " ": 	# El número de rollo está vacío
                utils.dialogo_info('ROLLO NO SELECCIONADO', 'Debe seleccionar un rollo.\nPara eliminar una incidencia use «Eliminar incidencia».', padre = self.wids['ventana'])
            else:
                articulo = pclases.Articulo.get(id)
                try:
                    rollo = articulo.rollo
                    rolloDefectuoso = articulo.rolloDefectuoso
                    descontar_material_adicional(self, articulo, restar = False)
                    articulo.parteDeProduccion = None
                    articulo.rollo = None
                    articulo.rolloDefectuoso = rolloDefectuoso
                    articulo.parteDeProduccion = None
                    articulo.destroySelf()
                    if rollo != None:
                        rollo.destroySelf()
                    if rolloDefectuoso != None:
                        rolloDefectuoso.destroySelf()
                except:
                    utils.dialogo_info(titulo = 'ERROR: ROLLO NO BORRADO', 
                                       texto = 'El rollo no ha sido eliminado completamente.\nVerifique que no haya sido vendido ya.\nAnote el número de rollo (%s) y contacte con el administrador de la aplicación\npara subsanar la inconsistencia.' % (rollo and rollo.codigo or "no disponible"), 
                                       padre = self.wids['ventana'])
                    # Mensaje y vuelvo a asociar el rollo, ya que no se ha eliminado al 
                    # tener alguna relación con algún otro objeto.
                    # rollo.parteDeProduccion = self.objeto
                    try:
                        articulo.sync()
                        articulo.rollo = rollo
                        articulo.rolloDefectuoso = rolloDefectuoso
                        articulo.parteDeProduccion = self.objeto
                        descontar_material_adicional(self, articulo, restar = True)
                    except pclases.SQLObjectNotFound: # Ya se ha borrado 
                        pass
                    except AttributeError:  # Existe el artículo pero ya no tiene bala
                        self.logger.error("El artículo ID %s ya no tiene rollo, no se ha podido sumar el material empleado al borrarlo y tampoco se pudo eliminar el artículo en sí." % articulo.id)
        self.actualizar_ventana()

    def add_incidencia(self, boton):
        ii = pclases.TipoDeIncidencia.select()
        idincidencia = utils.dialogo_combo('SELECCIONE UN TIPO DE INCIDENCIA', 
            'Seleccine un tipo de incidencia del desplegable inferior',
            [(i.id, i.descripcion) for i in ii], 
            padre = self.wids['ventana'])
        if idincidencia == None: 
            return
        utils.dialogo_info('HORA INICIO', 
            'A continuación seleccione la hora de inicio de la incidencia.', 
            padre = self.wids['ventana'])
        horaini = utils.mostrar_hora(time.localtime()[3], 0, 0, 'HORA INICIO')
        if horaini == None:
            return
        utils.dialogo_info('HORA FIN', 
            'A continuación seleccione la hora de finalización de la'
            ' incidencia.', 
            padre = self.wids['ventana'])
        horafin = utils.mostrar_hora(time.localtime()[3], 0, 0, 'HORA FIN')
        if horafin == None: 
            return
        self.objeto.sync()
        horaini = mx.DateTime.DateTimeFrom('%d-%2d-%2d %s' % 
                                            (self.objeto.fecha.year, 
                                             self.objeto.fecha.month, 
                                             self.objeto.fecha.day, 
                                             horaini))
        horafin = mx.DateTime.DateTimeFrom('%d-%2d-%2d %s' % 
                                            (self.objeto.fecha.year, 
                                             self.objeto.fecha.month, 
                                             self.objeto.fecha.day, 
                                             horafin))
        if horaini > horafin:
            horafin += mx.DateTime.oneDay
        while horaini < self.objeto.fechahorainicio:   # El parte está en la
                                # franja de medianoche y la incidencia 
                                # comienza después de las 12.
            horaini += mx.DateTime.oneDay   # Debe llevar la fecha del 
                                            # día siguiente.
            horafin += mx.DateTime.oneDay
        if entran_en_turno(self.objeto, horaini, horafin):
            observaciones = utils.dialogo_entrada(titulo = 'OBSERVACIONES', 
                texto = 'Introduzca observaciones sobre la incidencia:',
                padre = self.wids['ventana'])
            if observaciones == None:
                return
            incidencia = pclases.Incidencia(
                tipoDeIncidencia = pclases.TipoDeIncidencia.get(idincidencia),
                horainicio = horaini,
                horafin = horafin,
                parteDeProduccion = self.objeto,
                observaciones = observaciones)
            # NOTA: La BD está diseñada para soportar varios ítems en 
            # detallesdeproducción. De momento seguiré con 1 ítem por detalle.
            # Así que creo una nueva línea de detalle.
            self.actualizar_ventana()
        else:
            utils.dialogo_info(titulo = 'ERROR HORARIO', 
                texto = 'La franja horaria que ha seleccionado no entra '
                        'en el turno del parte.', 
                padre = self.wids['ventana'])

    def drop_incidencia(self, boton):
        model, paths = self.wids['tv_rollos'].get_selection().get_selected_rows()
        if paths == None or paths == []:
            utils.dialogo_info('INCIDENCIA NO SELECCIONADA', 
                               'Debe seleccionar la incidencia que desee eliminar del parte.', 
                               padre = self.wids['ventana'])
        else:
            if not utils.dialogo('¿Eliminar del parte?', 
                                 'BORRAR INCIDENCIAS DE CONTROL DE PRODUCCIÓN', 
                                 padre = self.wids['ventana']): 
                return
            for path in paths:
                id = model[path][-1]
                if model[path][1] != '': 	# El número de rollo NO está vacío
                    utils.dialogo_info('ROLLO SELECCIONADO', 
                                       'Ha seleccionado una rollo en lugar de una incidencia.\nUse «Quitar rollo» para eliminarla.', 
                                       padre = self.wids['ventana'])
                else:
                    incidencia = pclases.Incidencia.get(id)
                    incidencia.parteDeProduccion = None
                    try:
                        incidencia.destroySelf()
                    except:
                        utils.dialogo_info(titulo = 'INCIDENCIA NO ELIMINADA', 
                                           texto = 'Ocurrió un error al intentar eliminar la incidencia.', 
                                           padre = self.wids['ventana'])
            self.actualizar_ventana()

    def add_empleado(self, w):
        empleados = pclases.Empleado.select(pclases.AND(
                            pclases.Empleado.q.activo == True, 
                            pclases.Empleado.q.planta == True), 
                        orderBy = 'apellidos')
        empleados = [(e.id, e.nombre, e.apellidos) for e in empleados \
                     if e.planta and \
                        e.activo and \
                        e.categoriaLaboral and \
                        e.categoriaLaboral.planta] 
                        # e.categoriaLaboral.planta and \
                        # e.categoriaLaboral.lineaDeProduccion == self.linea)]
        ids = utils.dialogo_resultado(filas = empleados, 
                                      titulo = 'SELECCIONE EMPLEADOS', 
                                      cabeceras = ('ID', 'Nombre', 'Apellidos'),
                                      multi = True,
                                      padre = self.wids['ventana'])
        if ids == [-1]:
            return
        for id in ids:
            try:
                e = pclases.Empleado.get(id)
                self.objeto.addEmpleado(e)
            except:
                utils.dialogo_info(titulo = 'NÚMERO INCORRECTO', 
                                   texto = 'El empleado con código '
                                           'identificador %d no existe o '
                                           'no se pudo agregar.' % id, 
                                   padre = self.wids['ventana'])
        self.rellenar_tabla_empleados()

    def drop_empleado(self, w):
        if self.wids['tv_empleados'].get_selection().count_selected_rows() == 0:
            return
        model, path = self.wids['tv_empleados'].get_selection().get_selected()
        id = model[path][0]     # El id del empleado es la columna 0
        e = pclases.Empleado.get(id)
        self.objeto.removeEmpleado(e)
        self.rellenar_tabla_empleados()

    def rellenar_tabla_empleados(self):
        model = self.wids['tv_empleados'].get_model()
        model.clear()
        horas_parte = self.objeto.get_duracion()
        for ht in self.objeto.horasTrabajadas:
            try:
                supera_duracion_parte = ht.horas > horas_parte
            except TypeError:
                supera_duracion_parte = (
                    utils.DateTime2DateTimeDelta(ht.horas) > horas_parte)
            if supera_duracion_parte:
                ht.horas = horas_parte.strftime('%H:%M')
                ht.sync()
            model.append((ht.empleado.id, 
                          ht.empleado.nombre, 
                          ht.empleado.apellidos, 
                          ht.horas.strftime('%H:%M'), 
                          ht.id))

    def cambiar_partida(self, w):
        """
        Pide un número de partida por teclado y cambia a él. 
        """
        texto = """
        Al cambiar la partida del parte, se cambiará la partida de              
        todos los productos relacionados con él, así como el artículo           
        al que pertencen los productos.                                         
        Si quiere comenzar la producción de una nueva partida sin afectar       
        a los ya existentes, cree un nuevo parte."""
        if (self.objeto.articulos != [] 
            and not utils.dialogo(titulo = '¿ESTÁ SEGURO?', 
                                  texto = texto, 
                                  padre = self.wids['ventana'])):
            return 
        codigo = utils.dialogo_entrada(titulo = '¿NÚMERO DE PARTIDA?', 
                    texto = 'Introduzca el número de partida de geotextiles '\
                            'a fabricar:', 
                    padre = self.wids['ventana'])
        if codigo == None:  # Cancel
            return
        try:
            codigo = int(codigo.upper().replace("P-", ""))
            partida = pclases.Partida.select(
                        pclases.Partida.q.numpartida == codigo)[0]
        except (TypeError, ValueError), msg:
            self.logger.error("partes_de_fabricacion_rollos::cambiar_partida "\
                              "-> Código partida: %s. Excepción capturada: %s" 
                              % (codigo, msg))
            return
        except IndexError:
            utils.dialogo_info(titulo = "PARTIDA NO ENCONTRADA", 
                texto = "No se encontró la partida de producción.\nDebe carga"\
                        "r la línea con materia prima y crear la partida ante"\
                        "s de producir.", 
                padre = self.wids['ventana'])
            return
        # Tengo ya la partida seleccionada. Miro si hay una anterior y si tiene
        # al menos 1 rollo, para evitar que queden partidas vacías.
        # XXX: DONE: Hasta que JMadrid me lo confirme, esto queda en espera.
        #            Confirmado por correo el día 11/09/2008
        try:
            anterior = pclases.Partida.selectBy(
                numpartida = partida.numpartida - 1)[0]
        except IndexError:
            # Para producir, la partida debe existir porque se crea desde 
            # otra ventana. Ya no se crean aquí directamente. Si no hay 
            # numpartida-1 es porque el usuario encargado de las partidas 
            # de carga no ha creado la partida de geotextiles o bien es la 
            # primera partida del sistema.
            pass
        else:   # Hay partida anterior.
            if (anterior.esta_vacia() and (
                self.usuario == None or self.usuario.nivel > 2)):
                # Muestro el diálogo e impido pasar de partida solo si hay un 
                # usuario registrado y no tiene un nivel de privilegios "alto".
                utils.dialogo_info(titulo = "PARTIDA INCORRECTA", 
                    texto = "La partida anterior (%s) está vacía. No puede "\
                            "iniciar la partida nueva %s." % (
                                anterior.codigo, partida.codigo), 
                    padre = self.wids['ventana'])
                return
        # XXX XXX XXX XXX XXX XXX XXX XXX XXX XXX XXX XXX XXX XXX XXX XXX XXX
        # Pongo la partida como actual.
        partida_carga = partida.partidaCarga
        self.wids['e_partida'].set_text(partida_carga.codigo)
        self.wids['e_partida_gtx'].set_text(partida.codigo)
        if partida.rollos: # Ya tiene algún rollo asociado de un parte anterior
            productoVenta = partida.rollos[0].articulos[0].productoVenta
            self.producto = productoVenta
            self.rellenar_datos_articulo(self.producto)
            self.wids['e_fichaproduccion'].set_text(
                self.producto.camposEspecificosRollo.fichaFabricacion)
            self.objeto.fichaproduccion \
                = self.wids['e_fichaproduccion'].get_text()
        for a in self.objeto.articulos: # Y cambio de partida los artículos y 
                                        # de producto de venta.
            a.partida = partida
            a.productoVenta = self.producto
        self.actualizar_ventana()

    def nueva_partida(self, numpartida):
        """ Marcado para DEPRECATED """
        if isinstance(numpartida, type("¡Hola hombre cangrejo!")):
            numpartida = numpartida.upper().replace("P-", "")
        partida = pclases.Partida(numpartida = numpartida,
                                  codigo = "P-%s" % (numpartida))
        partida_actual = self.get_partida()
        if partida_actual != None:
            for b in partida_actual.balas:  # Cambio de partida las balas 
                b.partida = partida         # ANTES de cambiar el Entry 
                                            # (porque get_partida se obtiene 
                                            # de ahí).
        self.wids['e_partida'].set_text(str(numpartida))
        for a in self.objeto.articulos:
            a.partida = partida
        self.actualizar_ventana()

    def get_consumos_estimados(self, partida):
        """
        Devuelve la suma de los consumos estimados de todos los
        partes que pertenecen al objeto partida recibido.
        """
        consumos_estimados = 0
        rollos = partida.rollos
        for rollo in rollos:
            try:
                metros = rollo.articulos[0].productoVenta.camposEspecificosRollo.metrosLineales
                producto = rollo.articulos[0].productoVenta
                peso_rollo = metros * producto.camposEspecificosRollo.ancho * producto.camposEspecificosRollo.gramos/1000
                merma = rollo.articulos[0].parteDeProduccion.merma
                consumo_rollo = peso_rollo / (1.0 - merma)
                consumos_estimados += consumo_rollo
            except IndexError:
                self.logger.error("partes_de_fabricacion_rollos.py::get_consumos_estimados -> ¡No se encontraron artículos en el rollo ID %d!" % (rollo.id))
        return consumos_estimados
 
    def rellenar_balas(self):
        """ DEPRECATED """
        self.wids['frame3'].set_property("visible", False)
        return  # Se quita de aquí para meterlo en una ventana independiente.
        # NOTA: PLAN: Esto tarda lo más grande. Es lo que hace a esta ventana tan lenta respecto a los rollos.
        #model = self.wids['tv_balas'].get_model()
        #model.clear()
        #cantidad = 0
        #partida = self.get_partida()
        #if partida != None:
        #    consumos_estimados = self.get_consumos_estimados(partida)
        #    for bala in partida.balas:
        #        if consumos_estimados >= bala.pesobala: # Se ha gastado la bala entera.
        #            porcion_consumida = 100
        #            consumos_estimados -= bala.pesobala
        #        else:
        #            porcion_consumida = (consumos_estimados /  bala.pesobala) * 100  # % consumido
        #            consumos_estimados = 0      # Ya no puedo descontar más o me quedaré por debajo de 0.
        #        model.append((bala.codigo, bala.pesobala, porcion_consumida, bala.id))
        #        cantidad += bala.pesobala
        #self.wids['e_total_balas'].set_text('%s' % (utils.float2str(round(cantidad, 2))))
        ### self.wids['e_consumo_real'].set_text('%.2f' % round(cantidad, 2))
        #self.colorear_pesos()

    def get_partida(self):
        """
        Devuelve la partida relacionada con el parte actual.
        Si no hay partida definida devuelve None.
        """
        try:
            numpartida = self.wids['e_partida_gtx'].get_text()
            numpartida = numpartida.upper().replace("P-", "")
            numpartida = int(numpartida)
            return pclases.Partida.select(pclases.Partida.q.numpartida == numpartida)[0]
            # Numpartida es UNIQUE. Devuelve una partida o ninguna.
        except ValueError:
            # No hay un número en el Entry.
            return None
        except:
            return None

    def pedir_rango_balas(self):
        """
        Pide un rango de números de balas.
        Devuelve un generador de números
        de bala que comienza en el primero 
        del rango (o único, si solo se teclea uno)
        y acaba en el último del rango.
        """
        rango = utils.dialogo_entrada(titulo = 'INTRODUZCA RANGO',
                                      texto = 'Rango de números de bala o el código indovidual.\nEscriba el rango de códigos de la forma "xxxx-yyyy", ambos inclusive.',
                                      padre = self.wids['ventana'])
        articulos = []
        if rango == '' or rango == None:
            return rango
        try:
            if '-' in rango:
                ini, fin = rango.split('-')
                ini = int(ini)
                fin = int(fin)
                if fin < ini: 
                    ini, fin = fin, ini
            else:
                ini = int(rango)
                fin = ini
        except:
            utils.dialogo_info(titulo = 'CÓDIGO INCORRECTO', texto = 'Los códigos deben ser numéricos.\n\nVerifique que los ha escrito correctamente y que ha separado el rango con un guión.', padre = self.wids['ventana'])
            return []
        return xrange(ini, fin+1)

    def add_bala(self, w):
        """ DEPRECATED """
        if self.get_partida() == None:
            utils.dialogo_info(titulo = 'ELIJA PARTIDA', texto = 'Debe seleccionar antes una partida.', padre = self.wids['ventana'])
            return
        rango = self.pedir_rango_balas()
        if rango == None:
            return
        elif rango == '':
            balas = pclases.Bala.select(pclases.Bala.q.partidaID == None)
            balas = [(b.id, b.numbala, b.pesobala) for b in balas if b.analizada()]
            resp = utils.dialogo_resultado(balas, 
                                           'SELECCIONE BALAS', 
                                           cabeceras = ('ID', 'Número de bala', 'Peso'), 
                                           multi = True)
            if resp == [-1]:  # Ha cancelado
                return
            partida = self.get_partida()
            for id in resp:
                bala = pclases.Bala.get(id)
                if bala.claseb:
                    if utils.dialogo(titulo = 'BALA MARCADA COMO BAJA CALIDAD',
                                     texto = 'La bala está marcada como clase B. Esto puede provocar\nproblemas en la línea de producción.\n¿Está seguro de querer comsumir la bala de fibra?', 
                                     padre = self.wids['ventana']):
                        bala.partida = partida
        else:
            for numbala in rango:
                try:
                    balas = pclases.Bala.select(pclases.AND(pclases.Bala.q.numbala == numbala,
                                                            pclases.Bala.q.partidaID == None))
                    bala = [b for b in balas if b.analizada()][0]
                    # Numbala es UNIQUE. Sólo encontrará uno (o ninguno). 
                    # Busco sólo entre las balas no usadas con otra partida.
                    bala.partida = self.get_partida()
                except:
                    if balas.count() == 0:
                        utils.dialogo_info(titulo = 'BALA INCORRECTA',
                                           texto = """El número de bala %d no se encontró en el almacén.""" % numbala, 
                                           padre = self.wids['ventana'])
                    else:
                        utils.dialogo_info(titulo = 'LOTE NO ANALIZADO',
                                           texto = """
                        El lote %s al que pertenece la bala aún no ha sido analizado.
                        Hasta que no se especifiquen desde laboratorio las características del lote,                 
                        la bala %d no podrá ser usada en producción.
                        """ % (balas[0].lote.codigo, balas[0].numbala), 
                                           padre = self.wids['ventana'])
                    return
        self.rellenar_balas()

    def drop_bala(self, w):
        """ DEPRECATED """
        model, paths = self.wids['tv_balas'].get_selection().get_selected_rows()
        if not paths:
            return
        for path in paths:
            idbala = model[path][-1]
            bala = pclases.Bala.get(idbala)
            bala.partida = None
        self.rellenar_balas()

    def button_clicked(self, list, event):
        if event.button == 3:
            # menu = gtk.Menu()
            #ui_string = """<ui>
            #                <popup name='Popup'>
            #                    <menuitem action='Enviar muestra'/>
            #                    <menuitem action='Marcar como defectuoso'/>
            #                    <menuitem action='Limpiar marcas defectuoso y muestra'/>
            #                </popup>
            #               </ui>"""
            ui_string = """<ui>
                            <popup name='Popup'>
                                <menuitem action='Enviar muestra'/>
                                <menuitem action='Limpiar marcas defectuoso y muestra'/>
                            </popup>
                           </ui>"""
            ag = gtk.ActionGroup('WindowActions')
            #actions = [('Enviar muestra', gtk.STOCK_COLOR_PICKER, '_Enviar muestra', '<control>e',
            #            'Envia una muestra del lote o partida correspondiente al parte a laboratorio.', 
            #            self.enviar_a_laboratorio),
            #           ('Marcar como defectuoso', gtk.STOCK_DELETE, '_Marcar como defectuoso', '<control>m',
            #            'Marca el rollo seleccionado como defectuoso (peso inferior, gramaje bajo, longitud incorrecta, etc.).', 
            #            self.marcar_como_defectuoso),
            #           ('Limpiar marcas defectuoso y muestra', gtk.STOCK_CLEAR, '_Limpiar marcas defectuoso y muestra', '<control>l',
            #            'Limpia las marcas de defectuoso y la de muestra de laboratorio del rollo, si las tuviera.', 
            #            self.limpiar_marcas)]
            actions = [('Enviar muestra', gtk.STOCK_COLOR_PICKER, '_Enviar muestra', '<control>e',
                        'Envia una muestra del lote o partida correspondiente al parte a laboratorio.', 
                        self.enviar_a_laboratorio),
                       ('Limpiar marcas defectuoso y muestra', gtk.STOCK_CLEAR, '_Limpiar marca muestra', '<control>l',
                        'Limpia las marcas de muestra de laboratorio del rollo, si la tuviera. No cancela la muestra ya enviada.', 
                        self.limpiar_marcas)]
            ag.add_actions(actions)
            ui = gtk.UIManager()    #gtk.UI_MANAGER_POPUP
            ui.insert_action_group(ag, 0)
            ui.add_ui_from_string(ui_string)
            widget = ui.get_widget("/Popup")
            model, paths = self.wids['tv_rollos'].get_selection().get_selected_rows()
            mostrar_muestra = mostrar_defectuoso = True; mostrar_limpiar = False
            for path in paths:
                if model[path][1] != '':	# Nº rollo, tiene, no es una incidencia.
                    id = model[path][-1]
                    articulo = pclases.Articulo.get(id)
                    if articulo.es_rollo():
                        rollo = articulo.rollo
                        mostrar_muestra = mostrar_muestra and not(rollo.muestra)
                        mostrar_defectuoso = mostrar_defectuoso and not(rollo.rollob)
                        mostrar_limpiar = mostrar_limpiar or (rollo.muestra or rollo.rollob)
                    elif articulo.es_rollo_defectuoso():
                        rollo = articulo.rolloDefectuoso
                        mostrar_muestra = mostrar_limpiar = mostrar_defectuoso = False
                else:
                    mostrar_muestra = mostrar_defectuoso = mostrar_limpiar = False
            menuitem = ui.get_widget("/Popup/Enviar muestra")
            menuitem.set_sensitive(mostrar_muestra)
            #menuitem = ui.get_widget("/Popup/Marcar como defectuoso")
            #menuitem.set_sensitive(mostrar_defectuoso)
            menuitem = ui.get_widget("/Popup/Limpiar marcas defectuoso y muestra")
            menuitem.set_sensitive(mostrar_limpiar)
            widget.popup(None, None, None, event.button, event.time)
    
    def limpiar_marcas(self, parametro):
        """
        Marca el rollo seleccionado como defectuoso.
        """
        parte = self.objeto 
        if not parte.articulos:
            utils.dialogo_info(titulo = "PARTE VACÍO", texto = "En el parte seleccionado no hubo producción.", padre = self.wids['ventana'])
        else:
            model, paths = self.wids['tv_rollos'].get_selection().get_selected_rows()
            for path in paths:
                if model[path][1] != '':	# Nº rollo, tiene, no es una incidencia.
                    id = model[path][-1]
                    rollo = pclases.Articulo.get(id).rollo
                    if rollo != None:
                        rollo.rollob = False
                        rollo.muestra = False
                        rollo.observaciones = ''
                        model[path][-2] = rollo.observaciones

    def __crear_rollo_defectuoso_ye_olde_schoole(self):
        """
        Crea un rollo "defectuoso" según el modelo de datos 
        antiguo (marcándolo como rollo B pero siendo a todos 
        los efectos un rollo "normal", del mismo modo que se 
        hace con las balas), sin crearlo como artículo tipo 
        "rollo defectuoso" como se hace ahora.
        """
        parte = self.objeto 
        if not parte.articulos:
            utils.dialogo_info(titulo = "PARTE VACÍO", 
                texto = "En el parte seleccionado no hubo producción.", 
                padre = self.wids['ventana'])
        else:
            sel = self.wids['tv_rollos'].get_selection()
            model, paths = sel.get_selected_rows()
            for path in paths:
                if model[path][1] != '': # Nº rollo, tiene, no es incidencia.
                    id = model[path][-1]
                    rollo = pclases.Articulo.get(id).rollo
                    motivo = utils.dialogo_entrada(titulo = "MOTIVO", 
                                                   texto = "Introduzca el motivo por el cual el rollo %s se considera defectuoso:" % (rollo.codigo), 
                                                   padre = self.wids['ventana'])
                    if motivo != None:
                        largo = utils.dialogo_entrada(titulo = "LARGO",
                                                      texto = "Introduzca la longitud del rollo defectuoso:", 
                                                      valor_por_defecto = `rollo.productoVenta.camposEspecificosRollo.metrosLineales`, 
                                                      padre = self.wids['ventana'])
                        if largo != None:
                            try:
                                largo = utils._float(largo)
                            except:
                                utils.dialogo_info(titulo = "ERROR", 
                                                   texto = "El número introducido %s no es correcto." % (largo), 
                                                   padre = self.wids['ventana'])
                            else:
                                pesosin = rollo.peso_sin
                                try:
                                    dens = pesosin / (rollo.productoVenta.camposEspecificosRollo.ancho * largo)
                                except ZeroDivisionError:
                                    dens = 0
                                rollo.densidad = dens 
                                rollo.rollob = True
                                rollo.observaciones += "Defectuoso: " + motivo 
                                model[path][-2] += "Defectuoso: " + motivo 
                                imprimir_etiqueta_de_rollo_defectuoso(rollo)
 

    def marcar_como_defectuoso(self, parametro):
        """
        Marca el rollo seleccionado como defectuoso.
        UNDOCUMENTED
        """
        # No creo que llegue a usarse nunca. De todas formas me reservo el derecho como administrador 
        # a crear rollos B, por si las moscas. También tengo derecho como español a comerme un 
        # bocadillo de panceta si quiero. ¡¿Me oye?!
        if self.usuario != None and self.usuario.nivel > 0:
            utils.dialogo_info(titulo = "FUNCIONALIDAD NO IMPLEMENTADA", 
                               texto = "Esta funcionalidad no puede ser usada todavía.", 
                               padre = self.wids['ventana'])
            return
        self.__crear_rollo_defectuoso_ye_olde_schoole()
   
    def enviar_a_laboratorio(self, parametro):
        # NOTA: Ni idea de qué es lo que traerá el parámetro, sólo me interesa
        # el parte que está seleccionado en el treeview.
        parte = self.objeto 
        if not parte.articulos:
            utils.dialogo_info(titulo = "PARTE VACÍO", texto = "En el parte seleccionado no hubo producción.", padre = self.wids['ventana'])
        else:
            a = parte.articulos[0]  # Al menos tiene 1 artículo. 
                                    # Con el primero me vale.
            if parte.es_de_balas():
                lote = a.bala.lote
                partida = None
            else:
                lote = None
                partida = a.partida
            codigo = self.crear_muestra(lote, partida)
            if codigo != '':
                model, paths = self.wids['tv_rollos'].get_selection().get_selected_rows()
                for path in paths:
                    if model[path][1] != '':    # Nº rollo, tiene, 
                                                # no es una incidencia.
                        id = model[path][-1]
                        rollo = pclases.Articulo.get(id).rollo
                        if rollo != None:
                            rollo.muestra = True
                            rollo.observaciones += '>>> Muestra %s' % codigo
                            model[path][-2] += '>>> Muestra %s' % codigo
  
    def crear_muestra(self, lote, partida):
        _codigo = ['']
        dialogo = gtk.Dialog("DATOS DE LA MUESTRA",
                             self.wids['ventana'],
                             gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                             (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT,
                              gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT))
        dialogo.set_transient_for(self.wids['ventana'])
        dialogo.connect("response", self.crear_muestra_ok_cancel, lote, partida, _codigo)
        texto = """
        Introduzca, si lo desea, los datos para la muestra          
        de%s número %d.
        """ % (partida and " la partida" or "l lote", 
               partida and partida.numpartida or lote.numlote)
        txt = gtk.Label(texto)
        dialogo.vbox.pack_start(txt)
        dialogo.vbox.pack_start(gtk.Label("\nCódigo de muestra:"))
        codigo = gtk.Entry()
        codigo.set_text("M(%s)" % (partida and partida.codigo or lote.codigo))
        dialogo.vbox.pack_start(codigo)
        dialogo.vbox.pack_start(gtk.Label("\nObservaciones:"))
        observaciones = gtk.Entry()
        dialogo.vbox.pack_start(observaciones)
        dialogo.vbox.show_all()
        dialogo.run()
        dialogo.destroy()
        return _codigo[0]
    
    def crear_muestra_ok_cancel(self, dialogo, respuesta, lote, partida, _codigo):
        if respuesta == gtk.RESPONSE_ACCEPT:
            codigo = dialogo.vbox.get_children()[2].get_text()
            observaciones = dialogo.vbox.get_children()[4].get_text()
            m = pclases.Muestra(lote = lote,
                                partida = partida,
                                codigo = codigo,
                                observaciones = observaciones,
                                pendiente = True,
                                envio = mx.DateTime.localtime(),
                                recepcion = None, 
                                loteCem = None)
            _codigo[0] = codigo
            if utils.dialogo(titulo = "MUESTRA ENVIADA",
                             texto = "Muestra creada, enviada y pendiente para su análisis en laboratorio.\n¿Desea enviar una alerta?", 
                             padre = self.wids['ventana']):
                usuarios = [(u.id, u.usuario) for u in pclases.Usuario.select(orderBy = 'usuario')]
                usuario = utils.dialogo_combo(titulo = "SELECCIONE USUARIO",
                                              texto = "Seleccione del desplegable inferior al usuario que quiere alertar acerca de la muestra.",
                                              ops = usuarios,
                                              padre = self.wids['ventana'])
                if usuario != None:
                    user = pclases.Usuario.get(usuario)
                    if m.codigo:
                        msj = "La muestra %s está " % m.codigo
                    else:
                        msj = "Tiene una muestra "
                    msj += "pendiente de analizar." 
                    user.enviar_mensaje(msj)

    def bloquear(self, ch, mostrar_alerta = True):
        # Si el parte tiene menos de un día y se encuentra bloqueado, dejo que lo pueda desbloquear cualquiera.
        if mx.DateTime.localtime() - self.objeto.fecha <= mx.DateTime.oneDay and (self.objeto.bloqueado or ch.get_active()):
            self.objeto.bloqueado = False
        elif ch.get_active() != self.objeto.bloqueado:
            # NEW!: Los partes bloqueados solo los pueden desbloquear usuarios con nivel <= 1.
            if self.objeto.bloqueado:
                if self.usuario and self.usuario.nivel <= 1: # and self.objeto.bloqueado and not ch.get_active():
                    self.objeto.bloqueado = False
            else:
                if "w" in self.__permisos:  # Tiene permiso para bloquear el parte
                    self.objeto.bloqueado = True 
                else:
                    if mostrar_alerta:
                        utils.dialogo_info(titulo = "USUARIO SIN PRIVILEGIOS", 
                                           texto = "No tiene permisos suficientes para bloquear y verificar partes de producción.",
                                           padre = self.wids['ventana'])
        self.objeto.sync()
        self.objeto.make_swap()
        ch.set_active(self.objeto.bloqueado)
    
    def imprimir(self, boton):
        self.guardar(None)
        import informes
        parte = self.objeto
        ws = ('e_fecha', 'e_grsm2', 'sp_merma', 'e_partida', 'e_articulo', 
              'e_ancho', 'e_long_rollo', 'e_hora_ini', 'e_hora_fin', 
              'e_tiempo_total', 'e_o11', 'e_num_rollos', 'e_metros_lineales', 
              'e_peso_total', 'e_tiempo_real_trabajado', 'e_productividad', 
              'e_consumo_estimado')
        datos = {}
        for w in ws:
             datos[w] = self.wids[w].get_text()
        empleados = []
        for h in parte.horasTrabajadas:
            empleados.append(h.empleado)
        datos['empleados'] = empleados
        bounds = self.wids['txt_observaciones'].get_buffer().get_bounds()
        datos['observaciones'] = self.wids['txt_observaciones'].get_buffer().get_text(bounds[0], bounds[1])
 
        detallesdeproduccion = [i for i in self.objeto.incidencias] + [a for a in self.objeto.articulos]
        detallesdeproduccion.sort(self.cmpfechahora_or_numrollo)
        lineas = []
        # Filas del TreeView
        for detalle in detallesdeproduccion:
            obs = self.observaciones(detalle)
            lineas.append((self.rollo(detalle),
                           utils.float2str(self.peso(detalle), 1), 
                           utils.float2str(self.densidad(detalle), 1),
                           self.motivo(detalle),
                           self.horaini(detalle),
                           self.horafin(detalle),
                           self.duracion(detalle),
                           obs))
        informes.abrir_pdf(geninformes.parteRollos(datos, lineas))
        
    def _dialogo_entrada(self, texto= '', titulo = 'ENTRADA DE DATOS', valor_por_defecto = '', padre=None, pwd = False):
        """
        Muestra un diálogo modal con un textbox.
        Devuelve el texto introducido o None si se
        pulsó Cancelar.
        valor_por_defecto debe ser un string.
        Si pwd == True, es un diálogo para pedir contraseña
        y ocultará lo que se introduzca.
        """
        ## HACK: Los enteros son inmutables, usaré una lista
        res = [None]
        de = gtk.Dialog(titulo,
                        padre,
                        gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                        (gtk.STOCK_OK, gtk.RESPONSE_OK,
                         gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
        de.connect("response", utils.respuesta_ok_cancel, res)
        txt = gtk.Label(texto)
        de.vbox.pack_start(txt)
        txt.show()
        input = gtk.Entry()
        input.set_visibility(not pwd)
        def pasar_foco(widget, event):
          if event.keyval == 65293 or event.keyval == 65421:
            de.action_area.get_children()[1].grab_focus()
        input.connect("key_press_event", pasar_foco)
        de.vbox.pack_start(input)
        input.show()
        input.set_text(valor_por_defecto)
        marcado = gtk.CheckButton("Mostrar etiqueta de marcado CE")
        marcado.set_active(True)
        de.vbox.pack_start(marcado)
        marcado.show()
        if len(titulo)<20:
          width = 100
        elif len(titulo)<60:
          width = len(titulo)*10
        else:
          width = 600
        de.resize(width, 80)
        de.run()
        de.destroy()
        if res[0]==False:
          return None, None
        return res[0], marcado.get_active()

        
    def etiquetas(self, boton):
        """
        Imprime las etiquetas de los 
        rollos del parte seleccionados 
        """
        sel = self.wids['tv_rollos'].get_selection()
        model, paths = sel.get_selected_rows()
        rollos_defecto = []
        for path in paths:
            rollos_defecto.append(model[path][1])
            rollos_defecto.sort()
        rollos_defecto = ', '.join(rollos_defecto)
        import informes
        entrada, mostrar_marcado = self._dialogo_entrada(
            titulo = 'ETIQUETAS', 
            texto = "Introduzca el número de rollo o el rango (usando '-') "
                    "que desea etiquetar:",
            valor_por_defecto = rollos_defecto,
            padre = self.wids['ventana'])
        if entrada != None:
            if '-' in entrada:
                rango = entrada.split('-')
                try:
                    a = int(rango[0])
                    b = int(rango[1])
                    if a<= b:
                        b += 1
                    else:
                        a, b = b, a+1
                except:
                    utils.dialogo_info(titulo = 'ERROR',
                        texto = 'Los números de rollos introducidos no son '
                                'válidos', 
                        padre = self.wids['ventana'])
                    return
                valido = True
                for i in range(a,b):
                    if not self.objeto.rolloEnParte(i):
                        valido = False
                        break
                if not valido:
                    utils.dialogo_info(titulo = 'ERROR',
                        texto = 'Los números de rollos introducidos no '
                                'pertecen al parte', 
                        padre = self.wids['ventana'])
                    return
                temp = []
                for i in range(a,b):
                    temp.append(
                        pclases.Rollo.select(pclases.Rollo.q.numrollo == i)[0])
            else:
                codigos = [cod.strip() for cod in entrada.split(",")]
                temp = []
                for codigo in codigos:
                    if codigo.startswith("R"):
                        try:
                            temp.append(pclases.Rollo.select(
                                    pclases.Rollo.q.codigo == codigo)[0])
                        except Exception, msg:
                            self.logger.error(
                                "partes_de_fabricacion_rollos::etiquetas -> %s"
                                    % (msg))
                    elif codigo.startswith("X"):
                        try:
                            temp.append(pclases.RolloDefectuoso.select(
                                pclases.RolloDefectuoso.q.codigo == codigo)[0])
                        except Exception, msg:
                            self.logger.error("partes_de_fabricacion_rollos"
                                              "::etiquetas -> %s" % (msg))
                    else:
                        pass #No lo encuentro, paso de dar un mensaje de error.
                for a in temp:
                    if (not self.objeto.rolloEnParte(a.codigo) 
                        and (self.usuario == None 
                             or self.usuario.usuario != 'admin')):
                        utils.dialogo_info(titulo = 'ERROR', 
                            texto = 'El número de rollo (%d) introducido no '
                                    'pertece al parte' % a, 
                            padre = self.wids['ventana'])
                        return
            rollos = []
            fetiqueta = None
            for r in temp:
                elemento, fetiqueta = build_etiqueta(r)
                rollos.append(elemento)
            if boton.name == "b_etiquetas":
                informes.abrir_pdf(
                    geninformes.etiquetasRollos(rollos, mostrar_marcado))
                    # Antiguas, 4 etiquetas por folio A4.
            elif boton.name == "b_etiq_peq":
                informes.abrir_pdf(
                    geninformes.etiquetasRollosEtiquetadora(rollos, 
                                                            mostrar_marcado, 
                                                            fetiqueta))
                    # Etiquetas térmicas pequeñas.

    def buscar_producto_compra(self, defecto = "", 
                               titulo_defecto = "PLÁSTICO ENVOLTORIO"):
        a_buscar = utils.dialogo_entrada(titulo = titulo_defecto, 
                    texto = 'Introduzca código o descripción del producto:', 
                    valor_por_defecto = defecto, 
                    padre = self.wids['ventana'])
        if a_buscar == None:
            return None
        productos = pclases.ProductoCompra.select(pclases.AND(
            pclases.OR(pclases.ProductoCompra.q.descripcion.contains(a_buscar),
                       pclases.ProductoCompra.q.codigo.contains(a_buscar)), 
            pclases.ProductoCompra.q.controlExistencias == True, 
            pclases.ProductoCompra.q.existencias > 0, 
            pclases.ProductoCompra.q.obsoleto == False))
        if productos.count() == 0:
            utils.dialogo_info(titulo = 'PRODUCTO NO ENCONTRADO', 
                        texto = 'Producto no encontrado o sin existencias.', 
                        padre = self.wids['ventana'])
            return None
        elif productos.count() > 1:
            filas = [(p.id, p.codigo, p.descripcion, p.existencias) 
                     for p in productos]
            idproducto = utils.dialogo_resultado(filas,
                    'SELECCIONE PRODUCTO',
                    cabeceras = ['ID', 'Código', 'Descripción', 'Existencias'], 
                    padre = self.wids['ventana'])
            if idproducto > 0:
                productos = [pclases.ProductoCompra.get(idproducto)]
            else:
                return None
        producto = productos[0]
        return producto

    def cambiar_plastico(self, b):
        self.plastico = self.buscar_producto_compra()
        self.wids['e_plastico'].set_text(self.plastico and self.plastico.descripcion or "SIN ENVOLVER")

    def _salir(self, w, event = None):
        if ("w" in self.__permisos 
            and self.objeto 
            and not self.objeto.bloqueado 
            and self.objeto.fecha < mx.DateTime.localtime()-mx.DateTime.oneDay
           ):  # Tiene permiso para bloquear el parte
            res = utils.dialogo(titulo = "DEBE VERIFICAR EL PARTE",
                                texto = "Antes de cerrar el parte debe verifi"
                                        "carlo.\n¿Marcar como verificado?",
                                padre = self.wids['ventana'], 
                                bloq_temp = ["Sí"])
            
            self.objeto.bloqueado = res
            self.wids['ch_bloqueado'].set_active(self.objeto.bloqueado)
            # return True
        if not self.salir(w, mostrar_ventana = event == None):
            # Devuelve True cuando se cancela el cierre de la ventana (por temas de event-chain).
            try:
                padre = self.wids['ventana']
            except KeyError:
                padre = None
            vpro = VentanaActividad(texto = "Comprobando disparo de alertas...",
                                    padre = padre)
            vpro.mostrar()
            linea = pclases.LineaDeProduccion.select(pclases.LineaDeProduccion.q.nombre.contains('de geotextiles'))
            linea = self.linea 
            vpro.mover()
            if linea == None:
                print "WARNING: La línea de geotextiles no está correctamente dada de alta."
                self.logger.warning("WARNING: La línea de geotextiles no está correctamente dada de alta.")
            else:
                vpro.mover()
                formulacion = linea.formulacion
                for ca in [ca_con_p for ca_con_p 
                           in formulacion.consumosAdicionales 
                           if ca_con_p.productoCompra != None 
                               and not ca_con_p.productoCompra.obsoleto]:
                    vpro.mover()
                    # Verifico que no haya productos bajo mínimos:
                    if ca.productoCompra.existencias<ca.productoCompra.minimo:
                        vpro.mover()
                        try:
                            v = pclases.Ventana.select(
                                pclases.Ventana.q.fichero 
                                    == "pedidos_de_compra.py")[0]
                        except IndexError:
                            txterror = "WARNING: ¡La ventana de pedidos de "\
                                       "compra SE HA PERDIDO!"
                            print txterror
                            self.logger.warning(txterror)
                        mensaje = "El producto %s tiene las existencias bajo mínimos. Considere hacer un pedido de compra." % ca.productoCompra.descripcion
                        for u in [p.usuario for p in v.permisos if p.nuevo]: 
                            vpro.mover()
                            u.enviar_mensaje(mensaje)
                    # Y Verifico que no haya existencias negativas:
                    if ca.productoCompra.existencias < 0:
                        vpro.mover()
                        try:
                            v = pclases.Ventana.select(
                                pclases.Ventana.q.fichero 
                                    == "pedidos_de_compra.py")[0]
                        except IndexError:
                            txterror = "WARNING: ¡La ventana de pedidos de "\
                                       "compra SE HA PERDIDO!"
                            print txterror
                            self.logger.error(txterror)
                        vpro.mover()
                        mensaje = "El producto %s tiene existencias NEGATIVAS. Corrija el error lo antes posible." % ca.productoCompra.descripcion
                        for u in [p.usuario for p in v.permisos if p.nuevo]: 
                            vpro.mover()
                            u.enviar_mensaje(mensaje)
            vpro.mover()
            vpro.ocultar()

    def add_empleados_calendario(self):
        """
        Añade los empleados planificados según el calendario laboral
        para la línea de producción.
        1.- Obtener el calendario para self.linea.
        2.- Obtener los laborables del calendario correspondiente a la fecha del objeto.
        3.- Filtrar los laborables en función del turno correspondiente a la hora del objeto.
        4.- Obtener los empleados del laborable resultante.
        5.- Eliminar los empleados actuales. (PREGUNTA ANTES DE HACERLO)
        6.- Insertarlos los nuevos en el parte.
        """
        if self.linea != None:
            idldp = self.linea.id
            CAL = pclases.CalendarioLaboral
            calendarios = CAL.select("""linea_de_produccion_id = %d AND 
                                        date_part('month', mes_anno) = %d AND 
                                        date_part('year', mes_anno) = %d""" \
                                        % (idldp, self.objeto.fecha.month, self.objeto.fecha.year))
            if calendarios.count() == 1:
                calendario = calendarios[0]
                empleados = self.get_empleados_de_calendario(calendario)
                # Si hay empleados
                if self.objeto.horasTrabajadas != []: 
                    # Si no son los mismos del calendario y los quiere borrar.
                    if [ht.empleado for ht in self.objeto.horasTrabajadas] != empleados \
                       and utils.dialogo(titulo = "¿ELIMINAR OPERARIOS?",
                                     texto = "El parte ya tiene empleados relacionados.\n¿Desea eliminarlos y asociar los definidos en el turno?", 
                                     padre = self.wids['ventana']):
                        for ht in self.objeto.horasTrabajadas:
                            self.objeto.removeEmpleado(ht.empleado)
                    else:
                        # Si no los quiere borrar, cancelo todo.
                        return
                # Si no había empleados o no eran los mismos y los ha borrado.
                # Añado empleados de los laborables que cumplan el turno y sean de producción (no-recuperación).
                for empleado in empleados:
                    self.objeto.addEmpleado(empleado)
            elif calendarios.count() > 1:
                self.logger.error("partes_de_fabricacion_rollos.py -> Existe más de un calendario laboral para el mes, año y línea de producción: fecha %s - idldp %d - idparte %s." % (self.objeto.fecha, idldp, self.objeto.id))

    def get_empleados_de_calendario(self, calendario):
        res = []
        LAB = pclases.Laborable
        dia_lab_parte = self.objeto.fecha
        if isinstance(self.objeto.horainicio, 
                      type(mx.DateTime.DateTimeDelta(0))):
            seis_am = mx.DateTime.DateTimeDeltaFrom(hours = 6)
            medianoche = mx.DateTime.DateTimeDeltaFrom(hours = 0)
            restar_un_dia = lambda f: f - mx.DateTime.oneDay
        else:
            import datetime
            seis_am = datetime.time(6)
            medianoche = datetime.time(0)
            restar_un_dia = lambda f: f - datetime.timedelta(1)
        if self.objeto.horainicio >= medianoche and \
           self.objeto.horainicio <= seis_am and \
           self.objeto.horafin <= seis_am:  # No se mezclan turnos, esta 
                                # última comprobación podría no hacer falta.
            dia_lab_parte = restar_un_dia(dia_lab_parte)
        laborables = LAB.select("""calendario_laboral_id = %d 
                                   AND date_part('day', fecha) = %d""" 
                                    % (calendario.id, dia_lab_parte.day))
        for laborable in laborables:
            turno = laborable.turno
            if turno == None:
                mensaje = "partes_de_fabricacion_rollos.py::get_empleados_de_calendario -> Laborable ID %d no tiene turno relacionado. Intento eliminarlo de la BD." % (laborable.id)
                self.logger.error(mensaje)
                try:
                    laborable.destroySelf()
                    idlaborable = laborable.id
                    self.logger.warning("partes_de_fabricacion_rollos.py::get_empleados_de_calendario -> Registro laborable ID %d ELIMINADO SATISFACTORIAMENTE." % (idlaborable))
                except:
                    self.logger.error("partes_de_fabricacion_rollos.py::get_empleados_de_calendario -> Registro laborable ID %d NO ELIMINADO." % (laborable.id))
                print "ERROR: %s" % (mensaje)
                continue
            turnohorainicio = utils.DateTime2DateTimeDelta(turno.horainicio)
            turnohorafin = utils.DateTime2DateTimeDelta(turno.horafin)
            objetohorainicio = utils.DateTime2DateTimeDelta(self.objeto.horainicio)
            objetohorafin = utils.DateTime2DateTimeDelta(self.objeto.horafin)
            if not turno.recuperacion:
                ohi = objetohorainicio
                ohf = objetohorafin
                thi = turnohorainicio
                thf = turnohorafin
                if thi > thf: thf += mx.DateTime.oneDay
                if ohi > ohf: ohf += mx.DateTime.oneDay
                if ohi >= medianoche and ohi < seis_am: ohi += mx.DateTime.oneDay
                if ohf >= medianoche and ohf <= seis_am: ohf += mx.DateTime.oneDay
                if thi <= ohi <= thf and thi <= ohf <= thf:
                    for empleado in laborable.empleados:
                        res.append(empleado)
        return res

    def iniciar_pesaje_auto(self, boton):
        """
        Abre la ventana de pesaje automático.
        """
        rollo = None
        ventana_pesaje = crear_ventana_pesaje(self, 
                            padre = self.wids['ventana'], 
                            rollo = rollo, 
                            objeto_ventana_parte = self)

    def consumir_manual(self, boton):
        """
        Crea un registro de consumo manualmente y unifica los 
        consumos a continuación.
        Si algún consumo acaba con cantidad 0 (porque se haya 
        agregado un consumo negativo que haya restado a otro) 
        se elimina antes de salir de la rutina.
        """
        # Pedir producto(s) a consumir.
        producto, texto_buscado = utils.pedir_producto_compra(
            padre = self.wids['ventana'])
        # Pedir cantidad.
        if producto != None:
            unidad = ""
            try:
                producto_unidad = producto.unidad
                if producto_unidad != "":
                    unidad = " en %s" % (producto_unidad)
            except AttributeError, msg:
                self.logger.error("%sEl producto tipo %s ID %d no tiene atributo unidad. Excepción AttributeError: %s." 
                    % (self.usuario and self.usuario.usuario + ": " or "", 
                       type(producto), 
                       producto != None and producto.id or "NONE", 
                       msg))
            descripcion = producto.descripcion
            cantidad = utils.dialogo_entrada(titulo = "CANTIDAD", 
                                             texto = "Introduzca la cantidad a consumir de %s%s." % (descripcion, unidad), 
                                             padre = self.wids['ventana'])
            if cantidad != None:
                try:
                    cantidad_a_consumir = utils._float(cantidad)
                except (TypeError, ValueError):
                    utils.dialogo_info(titulo = "ERROR DE FORMATO", 
                                       texto = 'El texto introducido "%s" no es un número.' % (cantidad), 
                                       padre = self.wids['ventana'])
                else:
                    # Crear consumo.
                    producto.sync()
                    consumo = pclases.Consumo(silo = None, 
                                              parteDeProduccion = self.objeto, 
                                              productoCompra = producto, 
                                              actualizado = True, 
                                              antes = producto.existencias, 
                                              despues = producto.existencias - cantidad_a_consumir, 
                                              cantidad = cantidad_a_consumir)
                    # Actualizar existencias
                    producto.existencias -= cantidad_a_consumir
                    producto.add_existencias(-cantidad_a_consumir) 
                    producto.syncUpdate()
                    self.logger.warning("%sCONSUMO LÍNEA GEOTEXTILES -> PARTE %d -> Consumiendo manualmente %f %s de %s (ID %d). Existencias: %f."  
                                        % (self.usuario and self.usuario.usuario + ": " or "", 
                                           self.objeto.id, 
                                           cantidad_a_consumir, 
                                           producto.unidad, 
                                           producto.descripcion, 
                                           producto.id, 
                                           producto.existencias)) 
                    # Unificar consumos.
                    self.objeto.unificar_consumos()
                    actualizar_albaran_interno_con_tubos(self.objeto)
                    # Eliminar consumos con cantidad cero.
                    for c in self.objeto.consumos:
                        if round(c.cantidad, 3) == 0:
                            # Cosas tan pequeñas como las agujas se descuentan 
                            # en cantidades tan pequeñas que tras varias 
                            # inserciones y borrados puede quedar el consumo 
                            # con cantidad 0.0000...1, que debe ser borrado.
                            try:
                                c.destroySelf()
                            except Exception, msg:
                                self.logger.error("%sConsumo ID %d no se pudo eliminar. Excepción: %s" 
                                                  % (self.usuario and self.usuario.usuario + ": " or "", 
                                                     c.id, 
                                                     msg))
                    self.rellenar_tabla_consumos()
                    # Buscar y crear (si no existe) el albarán interno de consumos.
                    buscar_o_crear_albaran_interno(self.objeto)
                    actualizar_albaran_interno_con_tubos(self.objeto)

    def add_desecho(self, boton):
        """
        Crea un registro de consumo de material desechado y 
        actualiza la tabla.
        """
        producto = self.buscar_producto_compra(defecto = "", 
                            titulo_defecto = "BUSCAR PRODUCTO A DESECHAR")
        if producto != None:
            cantidad = utils.dialogo_entrada(titulo = "INTRODUZCA CANTIDAD", 
                        texto = "Teclee la cantidad que se desechará de %s:"%(
                            producto.descripcion), 
                        padre = self.wids['ventana'])
            if cantidad != None:
                try:
                    cantidad = utils._float(cantidad)
                except ValueError:
                    utils.dialogo_info(titulo = "ERROR EN FORMATO", 
                                       texto = "El texto tecleado %s no es un número válido." % (cantidad), 
                                       padre = self.wids['ventana'])
                else:
                    observaciones = utils.dialogo_entrada(titulo = "OBSERVACIONES", 
                                                          texto = "Teclee, si lo desea, el motivo por el cual la cantidad desechada de %s se considera defectuosa:" % (producto.descripcion),
                                                          padre = self.wids['ventana'])
                    if observaciones != None:
                        try:
                            desecho = pclases.DescuentoDeMaterial.desechar(producto, cantidad, self.objeto, observaciones)
                        except AssertionError, msg:
                            self.logger.error("%spartes_de_fabricacion_rollos::add_desecho -> AssertionError: %s" % (self.usuario and self.usuario.usuario + ": " or "", msg))
                        if desecho.cantidad != cantidad:
                            utils.dialogo_info(titulo = "EXISTENCIAS INSUFICIENTES", 
                                               texto = "La cantidad de %s en almacén era inferior a la cantidad tecleada (%s).\nSe ha descontado %s en su lugar." % (desecho.productoCompra.descripcion, utils.float2str(cantidad), utils.float2str(desecho.cantidad)), 
                                               padre = self.wids['ventana'])
                        self.objeto.unificar_desechos()
                        self.rellenar_tabla_desechos()

    def drop_desecho(self, boton):
        """
        Cancela el desecho seleccionado.
        """
        model, paths = self.wids['tv_desecho'].get_selection().get_selected_rows()
        if  paths != None and paths != []:
            for path in paths:
                idddm = model[path][-1]
                ddm = pclases.DescuentoDeMaterial.get(idddm)
                try:
                    ddm.anular()
                except AssertionError, msg:
                    self.logger.error("%spartes_de_fabricacion_rollos::drop_desecho -> AssertionError: %s" % (self.usuario and self.usuario.usuario + ": " or "", msg))
                    utils.dialogo_info(titulo = "ERROR", 
                                       texto = "Ocurrió un error anulando un descuento de material.\nPulse «Aceptar» para continuar.\n\n\n\nInformación de depuración:\n\n%s" % (msg), 
                                       padre = self.wids['ventana'])
                self.rellenar_tabla_desechos()
                self.objeto.unificar_desechos()


def descontar_material_adicional(ventana_parte, articulo, restar = True):
    """
    Descuenta el material adicional correspondiente al artículo según 
    la formulación que indique la línea de fabricación.
    Si "restar" es True, descuenta. Si es False, añade la cantidad (para
    cuando se elimine un rollo del parte, por ejemplo).
    Si es necesario, se dejará material con existencias en negativo, aunque
    se avisará al usuario de la incidencia.
    """
    producto = articulo.productoVenta
    # OJO: Debe llamarse "plastico", tal cual, sin acentos ni nada. No es lo 
    # suyo, pero al menos hemos reducido el número de casos especiales.
    for consumoAdicional in producto.consumosAdicionales:
        if (not consumoAdicional.productoCompra 
            or consumoAdicional.productoCompra.obsoleto):
            # Puede haber consumos que ya no se usan y símplemente se les ha 
            # quitado el producto a consumir para que no cuenten.
            continue
        if ("plastico" in consumoAdicional.nombre.lower() 
           and ventana_parte.plastico != None 
           and ventana_parte.plastico != consumoAdicional.productoCompra):
            consumido = consumoAdicional.consumir(articulo, 
                            cancelar = not restar, 
                            productoCompra = ventana_parte.plastico)
        else:
            consumido = consumoAdicional.consumir(articulo, 
                                                  cancelar = not restar)
        txtlog = "PARTE ID %s (%s, %s-%s): "\
            "Consumiendo %s de %s para %s %s. Existencias: %s" % (
                ventana_parte.objeto.id, 
                utils.str_fecha(ventana_parte.objeto.fecha), 
                utils.str_hora_corta(ventana_parte.objeto.horainicio), 
                utils.str_hora_corta(ventana_parte.objeto.horafin), 
                utils.float2str(consumido), 
                consumoAdicional.productoCompra 
                    and consumoAdicional.productoCompra.descripcion
                    or "... ¡NADA! ", 
                articulo.es_rollo() and "el rollo" or "la bolsa", 
                articulo.codigo, 
                consumoAdicional.productoCompra and 
                  utils.float2str(consumoAdicional.productoCompra.existencias)
                  or "-")
        try:
            ventana_parte.logger.warning(txtlog)
        except AttributeError:
            print txtlog
    ventana_parte.objeto.unificar_consumos()
    actualizar_albaran_interno_con_tubos(ventana_parte.objeto)

def _calcular_peso_densidad(peso, producto):
    """
    Calcula el peso y la "densidad" del artículo en base al 
    peso y producto recibido.
    Si el peso es None, usa los datos por defecto del producto.
    Si no lo es, devuelve el mismo peso recibido y la "densidad" 
    que le corresponde.
    """
    if peso == None:
        try:
            peso = ((producto.camposEspecificosRollo.gramos * producto.camposEspecificosRollo.ancho * producto.camposEspecificosRollo.metrosLineales)/1000) + producto.camposEspecificosRollo.pesoEmbalaje
        except TypeError:   # Lo ha dado por tener pesoEmbalaje = None y no poder sumar NoneType a float.
            txterror =  "partes_de_fabricacion_rollo.py::_calcular_peso_densidad -> El producto tiene campos de camposEspecificosRollo a None."
            print txterror
            if ventana_parte != None:
                ventana_parte.logger.error(txterror)
            peso = 0
        # Por defecto se crea con los datos fetén.
        densidad = producto.camposEspecificosRollo.gramos
    else:
        pesosin = (peso - producto.camposEspecificosRollo.pesoEmbalaje) * 1000
        try:
            dens = pesosin / (producto.camposEspecificosRollo.metros_cuadrados)
        except ZeroDivisionError:
            dens = 0
        densidad = dens 
    return peso, densidad

def crear_articulo(numrollo, 
                   partida, 
                   producto, 
                   parte, 
                   peso = None, 
                   objeto_ventana_parte = None, 
                   defectuoso = False):
    """
    Crea un artículo rollo con el número de rollo recibido, perteneciente a la 
    partida «partida», del producto indicado y con un artículo del parte 
    «parte». Si peso es None se le calcula el peso y densidad que le 
    correspondería por defecto según el producto.
    objeto_ventana_parte sería el objeto de la ventana del parte de 
    producción, para volcar al log si fuese necesario.
    Si "defectuoso" es True, se crea un rollo defectuoso en lugar de un rollo 
    "normal".
    OJO: AQUÍ NO SE DESCUENTA EL MATERIAL EMPLEADO EN LA FABRICACIÓN. Sólo se 
    crea el artículo.
    """
    peso, densidad = _calcular_peso_densidad(peso, producto)
    if not defectuoso:
        codigo = 'R%d' % (numrollo) # NOTA: Cambiar aquí si al final el 
                                    # código será distinto al número de rollo.
        rollo = pclases.Rollo(partida = partida,
                              codigo = codigo, 
                              numrollo = numrollo,
                              peso = peso,
                              densidad = densidad,
                              muestra = False, 
                              rollob = False) 
        rollod = None
    else:
        codigo = 'X%d' % (numrollo)  # NOTA: Cambiar aquí si al final el código será distinto al número de rollo.
        rollo = rollod = None
        observaciones = utils.dialogo_entrada(titulo = "OBSERVACIONES", 
                                              texto = "Introduzca el motivo por el cual el rollo se considera defectuoso:", 
                                              valor_por_defecto = "Defectuoso: longitud insuficiente.", 
                                              padre = objeto_ventana_parte.wids['ventana'])
        if observaciones != None:
            largo = utils.dialogo_entrada(titulo = "LARGO", 
                                          texto = "Introduzca la longitud en metros del rollo defectuoso:", 
                                          padre = objeto_ventana_parte.wids['ventana'])
            if largo != None and largo.strip() != "":
                try:
                    largo = utils._float(largo)
                except ValueError:
                    utils.dialogo_info(titulo = "ERROR",
                                       texto = "El texto %s no es un número válido." % (largo), 
                                       padre = objeto_ventana_parte.wids['ventana'])
                else:
                    ancho = producto.camposEspecificosRollo.ancho                   # Conserva el ancho del producto que se intentó fabricar.
                    pesoEmbalaje = producto.camposEspecificosRollo.pesoEmbalaje     # Conserva el peso del embalaje del producto original.
                    try:
                        densidad = ((peso - pesoEmbalaje) * 1000) / (largo * ancho)
                    except ZeroDivisionError:
                        densidad = 0.0
                    try:
                        rollod = pclases.RolloDefectuoso(partida = partida, 
                                                         numrollo = numrollo, 
                                                         codigo = codigo, 
                                                         observaciones = observaciones, 
                                                         peso = peso, 
                                                         densidad = densidad, 
                                                         metrosLineales = largo, 
                                                         ancho = ancho, 
                                                         pesoEmbalaje = pesoEmbalaje)
                    except Exception, msg:
                        txt = "Rollo defectuoso %s no se pudo crear. Probablemente número duplicado. Mensaje de la excepción: %s" % (codigo, msg)
                        print txt
    if rollo != None or rollod != None:
        articulo = pclases.Articulo(bala = None,
                            rollo = rollo,
                            rolloDefectuoso = rollod, 
                            parteDeProduccion = parte,
                            productoVenta = producto,
                            albaranSalida = None, 
                            almacen = pclases.Almacen.get_almacen_principal())
    else:
        articulo = None
    return articulo

def build_ventana(padre):
    """
    Construye un gtk.Window con los widgets 
    para el control del pesaje automático.
    """
    ventana = gtk.Window()
    ventana.set_title("LECTURA AUTOMÁTICA DE BÁSCULA")
    ventana.set_transient_for(padre)
    ventana.set_modal(True)
    contenedor = gtk.VBox()
    ventana.add(contenedor)
    box_rollo = gtk.HBox()
    box_rollo.add(gtk.Label("Código de rollo: "))
    e_numrollo = gtk.Entry()
    e_numrollo.set_property("editable", False)
    e_numrollo.set_property("has-frame", False)
    box_rollo.add(e_numrollo)
    b_cancelar = gtk.Button(stock = gtk.STOCK_CANCEL)
    l_peso = gtk.Label(
        '<big><span color="dark green">Esperando peso...</span></big>')
    l_peso.set_use_markup(True)
    l_peso.set_justify(gtk.JUSTIFY_CENTER)
    l_peso.set_property('xalign', 0.5)
    ch_marcado = gtk.CheckButton("_Marcado CE")
    ch_marcado.set_active(True)
    ch_defectuoso = gtk.CheckButton("_Defectuoso")
    ch_defectuoso.set_active(False)
    ch_defectuoso.connect("toggled",cambiar_marcado_ce,ch_marcado,e_numrollo)
    contenedor.add(box_rollo)
    contenedor.add(l_peso)
    contenedor.add(ch_marcado)
    contenedor.add(ch_defectuoso)
    contenedor.add(b_cancelar)
    ventana.resize(365, 150)
    ventana.move(435, 130)
    return ventana, l_peso, e_numrollo, b_cancelar, ch_marcado, ch_defectuoso

def cambiar_marcado_ce(ch_defectuoso, ch_marcado, e_numrollo):
    """
    Cambia el checkbox del marcado CD a Fase si se ha activado el 
    checkbox de defectuoso. En otro caso se pone a True.
    Si acaba marcado, cambia también el entry para mostrar el último 
    rollo defectuoso más 1. Si no, vuelve a poner el último rollo 
    más 1.
    """
    if ch_defectuoso.get_active():
        ch_marcado.set_active(False)
        codigo_proximo_rollo_defectuoso = pclases.RolloDefectuoso._connection.queryOne("SELECT ultimo_codigo_rollo_defectuoso_mas_uno();")[0]
        e_numrollo.set_text(codigo_proximo_rollo_defectuoso)
    else:
        ch_marcado.set_active(True)
        codigo_proximo_rollo = pclases.Rollo._connection.queryOne("SELECT ultimo_codigo_rollo_mas_uno();")[0]
        e_numrollo.set_text(codigo_proximo_rollo)

def get_puerto_serie():
    """
    Devuelve un objeto de pyserial con el puerto correspondiente abierto. 
    None si no se pudo abrir.
    La báscula debe estar en el COM2 en windows, 
    que el puerto que intentará abrir primero. Si no existe el 
    puerto o no hay nada conectado, intento con el 3 al 15 y por último el 1.
    En POSIX comienza por el 1 y si no lo consigue abrir intenta el 2.
    """
    try:
        import serial
    except ImportError:
        utils.dialogo_info(titulo = "ERROR IMPORTACIÓN", 
                           texto = "Debe instalar el módulo pyserial.", 
                           padre = None)
        return None
    import os
    if os.name == "posix":
        for numpuerto in range(16):
            try:
                com = serial.Serial("/dev/ttyS%d" % numpuerto)
                break
            except:
                com = None
    else:
        for numpuerto in [2] + range(3, 16) + [1]:
            try:
                com = serial.Serial("COM%d" % numpuerto)
                break
            except:
                com = None
    if com != None:     # Configuración protocolo simple EPELSA
        com.baudrate = 9600
        com.bytesize = 8
        com.parity = 'N'
        com.stopbits = 1
        com.timeout = None
        com.timeout = 0.5   # El timeout_add es bloqueante. Leeré cada segundo.
    return com

def cerrar_ventana_bascula(boton, ventana, com, src_id):
    """
    Cierra (destruye, más bien) la ventana de 
    pesaje y cierra el puerto serie.
    """
    import gobject
    gobject.source_remove(src_id)
    ventana.destroy()
    com.close()

def imprimir_etiqueta(articulo, marcado_ce, ventana_parte, defectuoso = False):
    """
    Crea y lanza un PDF con la etiqueta del artículo y el logotipo 
    de marcado CE si marcado_ce = True.
    Si "defectuoso" es False, imprime una etiqueta de rollo defectuoso.
    """
    if defectuoso:
        imprimir_etiqueta_de_rollo_defectuoso(articulo.rolloDefectuoso)
    else:
        if (articulo.rollo.numrollo > ventana_parte.ultima_etiqueta 
            or ventana_parte.ultima_etiqueta == None):
            import informes
            rollos = []
            producto = articulo.productoVenta
            try:
                campos = producto.camposEspecificosRollo
                if not campos.modeloEtiqueta:
                    fetiqueta = None    # Etiqueta estándar Geotexan
                else:
                    fetiqueta = campos.modeloEtiqueta.get_func()
            except AttributeError, e:  # No es un rollo.
                print "partes_de_fabricacion_rollos::imprimir_etiqueta "\
                      "-> AttributeError: No es un rollo.", e
                fetiqueta = None
                campos = None
            except ValueError, e:      # No tiene modelo de etiqueta.
                print "partes_de_fabricacion_rollos::imprimir_etiqueta "\
                      "-> ValueError: No es un rollo.", e
                fetiqueta = None
                campos = None
            if not campos:
                try:
                    ventana_padre = ventana_parte.wids['ventana']
                except (AttributeError, KeyError):
                    ventana_padre = None
                utils.dialogo_info(titulo = "ERROR ETIQUETA", 
                    texto = "Ocurrió un error al generar las etiquetas.\n"
                            "Intente crearlas manualmente usando el botón \n"
                            "correspondiente de la parte inferior de \n"
                            "la ventana.", 
                    padre = ventana_padre)
                return
            partida = articulo.rollo.partida.codigo
            if ventana_parte.ultima_etiqueta == None:
                kilos_fibra = 5500.0 * (1 - articulo.parteDeProduccion.merma) # OJO: Harcoded
                kilos_por_rollo = (campos.metros_cuadrados * campos.gramos) / 1000.0
                rollos_parte = int(kilos_fibra / kilos_por_rollo)
                ultima = articulo.rollo.numrollo + rollos_parte    # Mando a imprimir todos los rollos de la partida a no ser que ya se
                                                                   # hayan imprimido y sean rollos sueltos que han salido de más.
            else:
                ultima = articulo.rollo.numrollo + 1
            for numrollo in xrange(articulo.rollo.numrollo, ultima):
                elemento = {'descripcion': producto.nombre,
                            'densidad': str(campos.gramos),
                            'ancho': "%s m" % (campos.ancho),
                            'peso': "%s kg" % (
                                int((campos.metros_cuadrados 
                                     * campos.gramos 
                                     / 1000.0))), # PESO TEÓRICO. Sin embalaje.
                            'm2': "%s m²" % (campos.metros_cuadrados),
                            'mlin': "%s m" % (campos.metrosLineales),
                            'nrollo': str(numrollo),
                            'partida': partida, 
                            'codigo': producto.codigo, 
                            'codigo39': "R%d" % (numrollo),     # OJO: Si cambia la codificación de rollos, cambiar aquí.
                            'defectuoso': False, 
                            'idrollo': 0, 
                            'objeto': None,     # Si todavía no se ha creado, como defectuoso == False, geninformes no lo necesitará.
                            'productoVenta': articulo.productoVenta, 
                           }    # OJO: Si el formato de código de rollo cambia, también hay que cambiarlo aquí.
                rollos.append(elemento)
            # informes.mandar_a_imprimir_con_ghostscript(geninformes.etiquetasRollosEtiquetadora(rollos, marcado_ce))
            ventana_parte.ultima_etiqueta = ultima
            informes.abrir_pdf(geninformes.etiquetasRollosEtiquetadora(rollos, 
                                                                marcado_ce, 
                                                                fetiqueta))

def recv_serial(com, ventana, l_peso, ventana_parte, ch_marcado, e_numrollo, 
                ch_defectuoso, objeto_ventana_parte):
    #DEBUG:    print "callback lanzado. leyendo..."    # Tal y como suponía, esto es BLOQUEANTE con timeout_add.
    c = com.readline(eol = '\r') 
    #DEBUG:     print "leído: ", c
    if c.strip() != '':
        # Tratar
        try:
            peso = float(c)
        except Exception, msg:
            print "partes_de_fabricacion_rollos -> recv_serial", msg
            peso = 0
        if peso == 0:
            return True     # Cuando se apaga y enciende el peso, envía 0. Así que si el peso es 0, no creo rollo.
        l_peso.set_text(
            '<b><big><span color="dark green">%s</span></big></b>' 
                % (utils.float2str(peso)))
        l_peso.set_use_markup(True)
        #DEBUG:        print "Recibido peso: %f" % (peso)
        try:
            codigo_rollo_a_crear = get_proximo_codigo_a_crear(e_numrollo)
            partida = ventana_parte.get_partida()
            if partida != None:
                defectuoso = ch_defectuoso.get_active()
                numrollo = int(codigo_rollo_a_crear.upper().replace("R", "").replace("X", ""))  # Tanto si es normal como defectuoso, 
                                                            # con esto debería quedarme un entero que correspondería al número de rollo.
                articulo = crear_articulo(numrollo, partida, ventana_parte.producto, ventana_parte.objeto, peso = peso, objeto_ventana_parte = objeto_ventana_parte, defectuoso = defectuoso)
                if articulo != None:
                    descontar_material_adicional(ventana_parte, articulo)
                    imprimir_etiqueta(articulo, ch_marcado.get_active(), 
                                      ventana_parte, defectuoso)
            else:
                utils.dialogo_info(titulo = "SIN PARTIDA", 
                                   texto = "Cancele y seleccione una partida "
                                        "antes de introducir la producción.", 
                                   padre = ventana)
        except (psycopg_ProgrammingError, ValueError, AttributeError), msg:
            txterror = "partes_de_fabricacion_rollos::recv_serial -> %s" % (msg)
            print txterror
            utils.dialogo_info(titulo = 'ROLLO NO CREADO', 
                               texto = 'El rollo no se pudo crear. Vuelva a pesarlo.\n\n\nSi el error persiste, tal vez esta información pueda ser útil:\n\n%s' % (txterror), 
                               padre = ventana)
            return True
        ventana_parte.actualizar_ventana()
        # El recién creado lo pongo en la línea de última pesada.
        l_peso.set_text('<big><span color="dark green">Última pesada (%s): %s</span></big>' % (codigo_rollo_a_crear, l_peso.get_text()))
        # Y la variable ahora pasa a contener el siguiente rollo en base al último creado (dado que el checkbox permanece inmutable 
        # hasta que lo cambie el usuario, será del mismo tipo que el recién creado).
        codigo_rollo_a_crear = get_proximo_codigo_a_crear(e_numrollo)
        e_numrollo.set_text("%s" % (codigo_rollo_a_crear))
        l_peso.set_use_markup(True)
    return True 

def get_proximo_codigo_a_crear(e_numrollo):
    """
    A partir del entry devuelve el siguiente código de rollo a crear.
    Si lo que había era un número de rollo normal (Rxxxx) devuelve un 
    código de rollo normal. Si era un código de rollo defectuoso, 
    devuelve un código de rollo defectuoso (Xyyy).
    En cualquier caso se asegura de que el código devuelto esté realmente 
    disponible. Si en el lapso de tiempo en que se mostró el siguiente código 
    se han creado otros rollos, devuelve el siguiente a crear aunque no 
    coincida con el que estaba en pantalla (no debería ocurrir a no ser que 
    haya dos ordenadores creando rollos).
    """
    codigo_actual = e_numrollo.get_text()
    if codigo_actual.startswith("R"): 
        codigo_proximo_rollo = pclases.Rollo._connection.queryOne("SELECT ultimo_codigo_rollo_mas_uno();")[0]
    elif codigo_actual.startswith("X"):
        codigo_proximo_rollo = pclases.RolloDefectuoso._connection.queryOne("SELECT ultimo_codigo_rollo_defectuoso_mas_uno();")[0]
    else:
        codigo_proximo_rollo = pclases.Rollo._connection.queryOne("SELECT ultimo_codigo_rollo_mas_uno();")[0]
        print 'partes_de_fabricacion_rollos::get_proximo_codigo_a_crear -> No se pudo determinar el tipo de rollo a crear. Creo uno "normal": %s.' % (codigo_proximo_rollo)
    return codigo_proximo_rollo

def crear_ventana_pesaje(ventana_parte, padre = None, rollo = None, objeto_ventana_parte = None):
    """
    Crea una ventana de pesaje.
    Necesita python-serial.
    Se usa "COM1" como puerto si el sistema es MS-Windows. "/dev/ttyS0" o "/dev/ttyS1" (por este orden) 
    si el sistema es GNU/Linux.
    """
    import gobject
    com = get_puerto_serie()
    # DEBUG: print com
    if com != None:
        (ventana, 
         l_peso, 
         e_numrollo, 
         b_cancelar, 
         ch_marcado, 
         ch_defectuoso) = build_ventana(padre)
        # En WIN32 pyserial no tiene descriptor de fichero. :(
        # src_id = gobject.io_add_watch(com.fd, gobject.IO_IN | gobject.IO_HUP, recv_serial, com, ventana)
        src_id = gobject.timeout_add(1500, recv_serial, com, ventana, l_peso, 
                                     ventana_parte, ch_marcado, e_numrollo, 
                                     ch_defectuoso, objeto_ventana_parte)
        b_cancelar.connect("clicked", cerrar_ventana_bascula, ventana, com, 
                            src_id)
        ventana.connect("destroy", cerrar_ventana_bascula, ventana, com, src_id)
        if rollo == None:
            ultimo_mas_uno = pclases.Rollo._connection.queryOne(
                                """SELECT ultimo_codigo_rollo_mas_uno();""")
            proximo_codrollo = ultimo_mas_uno[0]
        else:
            proximo_codrollo = rollo.codigo
        e_numrollo.set_text("%s" % (proximo_codrollo))
        ventana.show_all()

def actualizar_albaran_interno_con_tubos(pdp):
    """
    CWT: En el albarán interno solo aparecen consumos manuales, sin embargo, 
    como era tradición que los tubos fueran así y ahora se han pasado a 
    automático, pues se ha decidido que los tubos sean un caso especial y 
    aparezcan en el albarán de consumos manuales aunque sean automáticos...
    CON TODO LO QUE ESO CONLLEVA.
    1.- Comprueba si hay consumos de tubos en el parte.
    2.- Si lo hay, comprueba si el parte tiene ya un albarán interno. Si no, 
        lo crea.
    3.- Del albarán elimina los consumos de tubos que haya.
    4.- Crea los consumos nuevos de acuerdo al parte, de manera que lo que 
        aparece en el albarán interno -respecto a tubos- y en el parte, 
        coincida.
    """
    cons_tubos = {}
    for c in pdp.consumos:
        if c.productoCompra.es_nucleo_carton():
            try:
                cons_tubos[c.productoCompra] += c.cantidad
            except KeyError:
                cons_tubos[c.productoCompra] = c.cantidad
    if not pdp.albaranInterno:
        buscar_o_crear_albaran_interno(pdp)
        actualizar_albaran_interno_con_tubos(pdp)
    for ldv in pdp.albaranInterno.lineasDeVenta:
        if ldv.productoCompra in cons_tubos:
            try:
                ldv.destroySelf()
            except Exception, msg:
                # ¿La LDV está relacionada con un pedido o algo "asina"?
                ldv.albaranSalida = None
                print "partes_de_fabricacion_rollos::No se pudo eliminar LDV ID %d de albarán interno %s. Elimino relación entre ellos." % (ldv.id, pdp.albaranInterno.numalbaran)
    for producto in cons_tubos:
        ldv = pclases.LineaDeVenta(productoCompra = producto, 
                                   cantidad = cons_tubos[producto], 
                                   precio = producto.precioDefecto, 
                                   albaranSalida = pdp.albaranInterno, 
                                   pedidoVenta = None, 
                                   facturaVenta = None, 
                                   productoVenta = None)


if __name__ == "__main__":
    p = PartesDeFabricacionRollos(permisos = "rx", usuario = pclases.Usuario.select(pclases.Usuario.q.usuario == "geotextil")[0])
    #p = PartesDeFabricacionRollos(permisos = "rxw", usuario = pclases.Usuario.select(pclases.Usuario.q.usuario == "admin")[0])
    #if len(sys.argv) > 1 and sys.argv[1] == "-b":
    #    crear_ventana_pesaje(None)  # Esto cascará, ya no me vale para hacer las pruebas unitarias.
    #    gtk.main()
    #else:
    #    p = PartesDeFabricacionRollos(permisos = "rxw")

