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
## centro_de_trabajo.py - Ventana de centroTrabajos.
###################################################################
## NOTAS:
##  
###################################################################
## Changelog:
## 24 de julio de 2006 -> Inicio.
## 
###################################################################
## DONE:
## + Tal vez todo el código de widgets dinámicos debería ir a la 
##   clase ventana.
##   Ya hay soporte para widgets dinámicos en widgets.py. Los de 
##   aquí se quedan ya como están.
###################################################################
from ventana import Ventana
import utils
import pygtk
pygtk.require('2.0')
import gtk, gtk.glade, time, sqlobject
import sys
try:
    import pclases
except ImportError:
    from os.path import join as pathjoin; sys.path.append(pathjoin("..", "framework"))
    import pclases
try:
    import geninformes
except ImportError:
    sys.path.append('../informes')
    import geninformes
from utils import _float as float
try:
    from psycopg import ProgrammingError as psycopg_ProgrammingError
except ImportError:
    from psycopg2 import ProgrammingError as psycopg_ProgrammingError


class CentrosDeTrabajo(Ventana):
    def __init__(self, objeto = None, usuario = None):
        """
        Constructor. objeto puede ser un objeto de pclases con el que
        comenzar la ventana (en lugar del primero de la tabla, que es
        el que se muestra por defecto).
        """
        Ventana.__init__(self, 'centros_de_trabajo.glade', objeto)
        connections = {'b_salir/clicked': self.salir,
                       'b_nuevo/clicked': self.crear_nuevo_centroTrabajo,
                       'b_actualizar/clicked': self.actualizar_ventana,
                       'b_guardar/clicked': self.guardar,
                       'b_buscar/clicked': self.buscar_centroTrabajo,
                       'b_borrar/clicked': self.borrar_centroTrabajo,
                      } 
        self.add_connections(connections)
        self.inicializar_ventana()
        if self.objeto == None:
            self.ir_a_primero()
        else:
            self.ir_a(objeto)
        gtk.main()

    def activar_widgets(self, s):
        """
        Activa o desactiva (sensitive=True/False) todos 
        los widgets de la ventana que dependan del 
        objeto mostrado.
        Entrada: s debe ser True o False. En todo caso
        se evaluará como boolean.
        """
        ws = ('t', )  
        for w in ws:
            self.wids[w].set_sensitive(s)

    def inicializar_ventana(self):
        """
        Inicializa los controles de la ventana.
        No crea los widgets dinámicos que dependen de los 
        campos del objeto dentro de la tabla «t».
        """
        self.activar_widgets(False)
        self.wids['b_actualizar'].set_sensitive(False)
        self.wids['b_guardar'].set_sensitive(False)
        self.wids['b_nuevo'].set_sensitive(True)
        self.wids['b_buscar'].set_sensitive(True)

    def comparar_campo(self, col, type_col):
        """
        Compara el contenido del widget cuyo nombre coincide con "col" 
        con el valor del objeto para el campo "col".
        "type_col" es el tipo SQLObject del atributo, se usa para 
        determinar cómo comparar los valores.
        """
        res = False
        if isinstance(type_col, sqlobject.SOStringCol):  # Cadena: el widget es un entry
            res = self.comparar_string(col)
        elif isinstance(type_col, sqlobject.SOIntCol):   # Entero: el widget es un entry
            res = self.comparar_int(col)
        elif isinstance(type_col, sqlobject.SOBoolCol):  # Boolean: el widget es un checkbox
            res = self.comparar_bool(col)
        elif isinstance(type_col, sqlobject.SOForeignKey):  # Entero-clave ajena: el widget es un comboboxentry
            res = self.comparar_ajena(col)
        elif isinstance(type_col, sqlobject.SOCol):      # Clase base, casi seguro Float: el widget es un entry
            res = self.comparar_float(col)
        else:
            print "categorias_laborales.py: No se pudo determinar el tipo de datos del campo %s." % col
            self.logger.error("categorias_laborales.py: No se pudo determinar el tipo de datos del campo %s." % col)
        return res

    def comparar_float(self, col):
        res = 0.0
        try:
            valor_ventana = self.wids[col].get_text()
        except KeyError:
            txt_error = "categorias_laborales.py: No se pudo obtener el valor de la ventana para %s." % col
            print txt_error
            self.logger.error(txt_error)
            valor_ventana = 0.0
        try:
            valor_ventana = float(valor_ventana)
        except ValueError:
            txt_error = "categorias_laborales.py: No se pudo convertir %s(%s) a float." % (col, valor_ventana)
            print txt_error
            self.logger.error(txt_error)
            valor_ventana = 0.0
        try:
            valor_campo = self.objeto._SO_getValue(col)
            if not isinstance(valor_campo, type(0.0)):   # Porque es posible que el SOCol no contenga un float.
                                                        # El SOCol es la clase base. Se asume flotante por eliminación.
                res = False
            else:
                res = valor_ventana == valor_campo
        except KeyError:
            txt_error = "categorias_laborales.py: No se pudo obtener el valor del objeto para %s." % col
            print txt_error
            self.logger.error(txt_error)
            valor_campo = 0.0
        return res

    def comparar_ajena(self, col):
        res = None
        try:
            valor_ventana = utils.combo_get_value(self.wids[col])
        except KeyError:
            txt_error = "categorias_laborales.py: No se pudo obtener el valor de la ventana para %s." % col
            print txt_error
            self.logger.error(txt_error)
            valor_ventana = None
        try:
            valor_campo = self.objeto._SO_getValue(col) # Es un ID -es decir, un entero-, no un objeto sqlobject.
        except KeyError:
            txt_error = "categorias_laborales.py: No se pudo obtener el valor del objeto para %s." % col
            print txt_error
            self.logger.error(txt_error)
            valor_campo = None
        res = valor_ventana == valor_campo
        return res

    def comparar_bool(self, col):
        res = False
        try:
            valor_ventana = self.wids[col].get_active()
        except KeyError:
            txt_error = "categorias_laborales.py: No se pudo obtener el valor de la ventana para %s." % col
            print txt_error
            self.logger.error(txt_error)
            valor_ventana = False
        try:
            valor_campo = self.objeto._SO_getValue(col)
        except KeyError:
            txt_error = "categorias_laborales.py: No se pudo obtener el valor del objeto para %s." % col
            print txt_error
            self.logger.error(txt_error)
            valor_campo = False
        res = valor_ventana == valor_campo
        return res

    def comparar_int(self, col):
        res = False
        try:
            valor_ventana = self.wids[col].get_text()
        except KeyError:
            txt_error = "categorias_laborales.py: No se pudo obtener el valor de la ventana para %s." % col
            print txt_error
            self.logger.error(txt_error)
            valor_ventana = ""
        try:
            valor_ventana = int(valor_ventana)
        except ValueError:
            txt_error = "categorias_laborales.py: No se pudo convertir %s a entero." % col
            print txt_error
            self.logger.error(txt_error)
            valor_ventana = 0
        try:
            valor_campo = self.objeto._SO_getValue(col)
        except KeyError:
            txt_error = "categorias_laborales.py: No se pudo obtener el valor del objeto para %s." % col
            print txt_error
            self.logger.error(txt_error)
            valor_campo = 0
        res = valor_ventana == valor_campo
        return res

    def comparar_string(self, col):
        res = False
        try:
            valor_ventana = self.wids[col].get_text()
        except KeyError:
            txt_error = "categorias_laborales.py: No se pudo obtener el valor de la ventana para %s." % col
            print txt_error
            self.logger.error(txt_error)
            valor_ventana = ""
        try:
            valor_campo = self.objeto._SO_getValue(col)
        except KeyError:
            txt_error = "categorias_laborales.py: No se pudo obtener el valor del objeto para %s." % col
            print txt_error
            self.logger.error(txt_error)
            valor_campo = ""
        res = valor_ventana == valor_campo
        return res

    def es_diferente(self):
        """
        Devuelve True si la información en pantalla es distinta a la
        del objeto en memoria.
        """
        centroTrabajo = self.objeto
        if centroTrabajo == None: return False

        condicion = True
        for col in centroTrabajo._SO_columnDict:
            condicion = condicion and self.comparar_campo(col, centroTrabajo._SO_columnDict[col])
        return not condicion	# Concición verifica que sea igual

    def aviso_actualizacion(self):
        """
        Muestra una ventana modal con el mensaje de objeto 
        actualizado.
        """
        utils.dialogo_info('ACTUALIZAR',
                           'El centroTrabajo ha sido modificado remotamente.\nDebe actualizar la información mostrada en pantalla.\nPulse el botón «Actualizar»')
        self.wids['b_actualizar'].set_sensitive(True)

    def ir_a_primero(self):
        """
        Hace que el primer registro -si lo hay- de la tabla implicada
        en el objeto del formulario sea el objeto activo.
        """
        centroTrabajo = self.objeto
        try:
            # Anulo el aviso de actualización del envío que deja de ser activo.
            if centroTrabajo != None: centroTrabajo.notificador.set_func(lambda : None)
            centroTrabajo = pclases.CentroTrabajo.select(orderBy="id")[0]
            centroTrabajo.notificador.set_func(self.aviso_actualizacion)
        except:
            centroTrabajo = None 	
        self.objeto = centroTrabajo
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
            filas_res.append((r.id,r.nombre)) 
        idcentroTrabajo = utils.dialogo_resultado(filas_res,
                                             titulo = 'Seleccione categoria laboral',
                                             cabeceras = ('Código (ID)', 'Centro de trabajo'))
        if idcentroTrabajo < 0:
            return None
        else:
            return idcentroTrabajo

    def rellenar_widgets(self):
        """
        Redimensiona «t» y crea dentro los widgets necesarios para
        mostrar y editar los campos de «objeto».
        """
        # HACK: Es para evitar el campo nónima, que ya no se usa:
        d = {}
        for c in self.objeto._SO_columnDict:
            if c != 'nomina' and c != 'preciohora':
                d[c] = self.objeto._SO_columnDict[c]
        self.objeto._SO_columnDict = d
        # END OF HACK
        numcampos = len(self.objeto._SO_columnDict)
        if numcampos % 2 != 0:
            numwidgets = numcampos + 1
        else:
            numwidgets = numcampos
        for child in self.wids['t'].get_children():
            child.destroy()
        self.wids['t'].resize(numwidgets / 2, 4)
        icol = 0
        irow = 0
        for col in self.objeto._SO_columnDict:
            if not isinstance(self.objeto._SO_columnDict[col], sqlobject.SOBoolCol):
                # Los checkboxes llevan su propio label.
                label = self.build_label(col)
                self.wids['t'].attach(label, icol, icol+1, irow, irow+1)
            icol += 1
            child = self.build_child(col, self.objeto._SO_columnDict[col])
            self.set_valor(child, col, self.objeto._SO_columnDict[col])
            self.wids['t'].attach(child, icol, icol+1, irow, irow+1)
            icol += 1
            if icol == 4:
                icol = 0
                irow += 1
        self.wids['t'].show_all()
        self.objeto.make_swap()

    def build_label(self, nombrecampo):
        """
        Construye la etiqueta correspondiente a "nombrecampo".
        """
        # XXX: Cambiar el diccionario según lo que se vaya a mostrar en pantalla.
        nombres = {'planta': 'Trabaja en planta',
                   'activo': 'Trabajador con alta en la empresa',
                   'categoriaLaboralID': 'Categoría laboral',
                   'centroTrabajoID': 'Centro de trabajo',
                   'dni': 'DNI',
                   }
        try:
            label = gtk.Label(nombres[nombrecampo])
        except KeyError: # Si no está, muestro el nombre del campo.
            label = gtk.Label(utils.descamelcase_o_matic(nombrecampo))
        label.set_property("xalign", 1)
        return label
        
    def build_child(self, nombrecampo, tipocampo):
        """
        Construye el widget correspondiente al tipo de campo recibido y 
        establece su valor por defecto.
        """
        res = gtk.Label('ERROR: N/A')
        if isinstance(tipocampo, sqlobject.SOStringCol):  # Cadena: el widget es un entry
            res = gtk.Entry()
            if tipocampo.default != None and tipocampo.default != sqlobject.sqlbuilder.NoDefault:
                res.set_text("%s" % (tipocampo.default))
        elif isinstance(tipocampo, sqlobject.SOIntCol):   # Entero: el widget es un entry
            res = gtk.Entry()
            if tipocampo.default != None and tipocampo.default != sqlobject.sqlbuilder.NoDefault:
                res.set_text("%s" % (tipocampo.default))
        elif isinstance(tipocampo, sqlobject.SOBoolCol):  # Boolean: el widget es un checkbox
            label = self.build_label(nombrecampo)
            res = gtk.CheckButton(label = label.get_text())
            if tipocampo.default:
                res.set_active(True)
        elif isinstance(tipocampo, sqlobject.SOForeignKey):  # Entero-clave ajena: el widget es un comboboxentry
            res = gtk.ComboBoxEntry()
            ajena = tipocampo.foreignKey
            clase = getattr(pclases, ajena)
            COLUMNATEXTO = 'nombre'     # XXX: Cambiar si no tiene una columna "nombre"
            try:
                contenido = [(r.id, r._SO_getValue(COLUMNATEXTO)) for r in clase.select(orderBy='id')]
            except KeyError:
                COLUMNATEXTO = 'puesto'     # XXX: Cambiar si no tiene una columna "puesto"
                contenido = [(r.id, r._SO_getValue(COLUMNATEXTO)) for r in clase.select(orderBy='id')]
            utils.rellenar_lista(res, contenido)
        elif isinstance(tipocampo, sqlobject.SOCol):      # Clase base, casi seguro Float: el widget es un entry
            res = gtk.Entry()
            if tipocampo.default != None and tipocampo.default != sqlobject.sqlbuilder.NoDefault:
                res.set_text(utils.float2str("%s" % tipocampo.default))
        else:
            txt = "categorias_laborales.py: No se pudo construir el widget para %s." % nombrecampo
            print txt
            self.logger.error(txt)
        res.set_name(nombrecampo)
        self.wids[nombrecampo] = res
        return res
        
    def set_valor(self, w, nombrecampo, tipocampo):
#        valor = self.objeto._SO_getValue(nombrecampo)
        get_valor = getattr(self.objeto, '_SO_get_%s' % (nombrecampo))
        valor = get_valor()
        if isinstance(tipocampo, sqlobject.SOStringCol):  # Cadena: el widget es un entry
            if valor != None:
                w.set_text(valor)
            else:
                w.set_text("")
        elif isinstance(tipocampo, sqlobject.SOIntCol):   # Entero: el widget es un entry
            try:
                w.set_text("%d" % valor)
            except TypeError:
                w.set_text("0")
        elif isinstance(tipocampo, sqlobject.SOBoolCol):  # Boolean: el widget es un checkbox
            w.set_active(valor)
        elif isinstance(tipocampo, sqlobject.SOForeignKey):  # Entero-clave ajena: el widget es un comboboxentry
            utils.combo_set_from_db(w, valor)
        elif isinstance(tipocampo, sqlobject.SOCol):      # Clase base, casi seguro Float: el widget es un entry
            if valor != None:
                try:
                    w.set_text(utils.float2str(valor))
                except ValueError:
                    w.set_text('0')
        else:
            txt = "categorias_laborales.py: No se pudo establecer el valor %s para %s." % (valor, w)
            print txt
            self.logger.error(txt)

    def get_valor(self, w, nombrecampo, tipocampo):
        res = None 
        if isinstance(tipocampo, sqlobject.SOStringCol):  # Cadena: el widget es un entry
            res = w.get_text()
        elif isinstance(tipocampo, sqlobject.SOIntCol):   # Entero: el widget es un entry
            res = w.get_text()
            try:
                res = int(res)
            except ValueError:
#                txt = "categorias_laborales.py: No se pudo convertir el valor %s de %s para %s <%s>." \
#                       % (res, w, nombrecampo, tipocampo)
#                print txt
#                self.logger.error(txt)
                txt = "El valor %s no es correcto. Introduzca un número entero." % (res)
                utils.dialogo_info(titulo = "ERROR DE FORMATO", texto = txt, padre = self.wids['ventana'])
                res = 0
        elif isinstance(tipocampo, sqlobject.SOBoolCol):  # Boolean: el widget es un checkbox
            res = w.get_active()
        elif isinstance(tipocampo, sqlobject.SOForeignKey):  # Entero-clave ajena: el widget es un comboboxentry
            res = utils.combo_get_value(w)
        elif isinstance(tipocampo, sqlobject.SOCol):      # Clase base, casi seguro Float: el widget es un entry
            res = w.get_text()
            try:
                res = float(res)
            except ValueError:
#                txt = "categorias_laborales.py: No se pudo convertir el valor %s de %s para %s <%s>." \
#                       % (res, w, nombrecampo, tipocampo)
#                print txt
#                self.logger.error(txt)
                txt = "El valor %s no es correcto. Introduzca un número." % (res)
                utils.dialogo_info(titulo = "ERROR DE FORMATO", texto = txt, padre = self.wids['ventana'])
                res = 0.0
        else:
            txt = "categorias_laborales.py: No se pudo obtener el valor de %s para %s <%s>." \
                   % (w, nombrecampo, tipocampo)
            print txt
            self.logger.error(txt)
        return res

    def borrar_centroTrabajo(self, widget):
        """
        Elimina el centroTrabajo de la tabla pero NO
        intenta eliminar ninguna de sus relaciones,
        de forma que si se incumple alguna 
        restricción de la BD, cancelará la eliminación
        y avisará al usuario.
        """
        centroTrabajo = self.objeto
        if not utils.dialogo('Se borrará el centroTrabajo actual.\n¿Está seguro?', 'BORRAR CATEGORÍA LABORAL'): 
            return
        if centroTrabajo != None: centroTrabajo.notificador.set_func(lambda : None)
        try:
            centroTrabajo.destroySelf()
        except: 
            utils.dialogo_info('CATEGORÍA LABORAL NO ELIMINADA', 'La categoria laboral está implicada en operaciones que impiden su borrado.\n(Por ejemplo, puede estar aún relacionada con centroTrabajos.)')
        self.ir_a_primero()
            
    def crear_nuevo_centroTrabajo(self, widget):
        """
        Función callback del botón b_nuevo.
        Pide los datos básicos para crear un nuevo objeto.
        Una vez insertado en la BD hay que hacerlo activo
        en la ventana para que puedan ser editados el resto
        de campos que no se hayan pedido aquí.
        """
        centroTrabajo = self.objeto
        if centroTrabajo!=None:
            centroTrabajo.notificador.set_func(lambda : None)
        centroTrabajo = pclases.CentroTrabajo(nombre = 'Introduzca aquí el nombre del centro de trabajo')
        utils.dialogo_info(titulo = 'NUEVO CENTRO DE TRABAJO CREADO',
                           texto = 'Introduzca los datos del centro de trabajo.\nRecuerde pulsar el botón GUARDAR cuando termine.\n', 
                           padre = self.wids['ventana'])
        self.wids['b_guardar'].set_sensitive(True)
        self.objeto = centroTrabajo
        self.actualizar_ventana()
        if centroTrabajo!=None:
            centroTrabajo.notificador.set_func(self.aviso_actualizacion)

    def buscar_centroTrabajo(self, widget):
        """
        Muestra una ventana de búsqueda y a continuación los
        resultados. El objeto seleccionado se hará activo
        en la ventana a no ser que se pulse en Cancelar en
        la ventana de resultados.
        """
        centroTrabajo = self.objeto
        objetobak = self.objeto
        a_buscar = utils.dialogo_entrada("Introduzca nombre o código del centro de trabajo.") 
        if a_buscar != None:
            if a_buscar != '':
                try:
                    criterio = sqlobject.OR(pclases.CentroTrabajo.q.nombre.contains(a_buscar),
                                            pclases.CentroTrabajo.q.id == int(a_buscar))
                except ValueError:
                    criterio = pclases.CentroTrabajo.q.nombre.contains(a_buscar)
            else:
                criterio = pclases.CentroTrabajo.q.nombre.contains(a_buscar)
            resultados = pclases.CentroTrabajo.select(criterio)  
            if resultados.count() > 1:
                ## Refinar los resultados
                idcentroTrabajo = self.refinar_resultados_busqueda(resultados)
                if idcentroTrabajo == None:
                    return
                resultados = [pclases.CentroTrabajo.get(idcentroTrabajo)]
            elif resultados.count() < 1:
                ## Sin resultados de búsqueda
                utils.dialogo_info('SIN RESULTADOS', 
                                   '\n\nLa búsqueda no produjo resultados.\nPruebe a cambiar el texto buscado o déjelo en blanco para ver una lista completa.\n(Atención: Ver la lista completa puede resultar lento si el número de elementos es muy alto)\n\n')
                return
            ## Un único resultado
            # Primero anulo la función de actualización
            if centroTrabajo != None:
                centroTrabajo.notificador.set_func(lambda : None)
            # Pongo el objeto como actual
            centroTrabajo = resultados[0]
            # Y activo la función de notificación:
            self.objeto = centroTrabajo
            self.actualizar_ventana(objetobak)
            centroTrabajo.notificador.set_func(self.aviso_actualizacion)

    def guardar(self, widget):
        """
        Guarda el contenido de los entry y demás widgets de entrada
        de datos en el objeto y lo sincroniza con la BD.
        """
        centroTrabajo = self.objeto
        # Desactivo el notificador momentáneamente
        centroTrabajo.notificador.set_func(lambda: None)
        # Actualizo los datos del objeto
        for col in centroTrabajo._SO_columnDict:
            valor = self.get_valor(self.wids[col], col, centroTrabajo._SO_columnDict[col])
            try:
                centroTrabajo._SO_setValue(col, valor, None, None)
            except psycopg_ProgrammingError:
                utils.dialogo_info(titulo = "ERROR", texto = "Se produjo un error al guardar uno de los valores.\nCompruebe que el formato y tipo de dato es correcto.", padre = self.wids['ventana']) 
        # Fuerzo la actualización de la BD y no espero a que SQLObject lo haga por mí:
        centroTrabajo.syncUpdate()
        # Vuelvo a activar el notificador
        centroTrabajo.notificador.set_func(self.aviso_actualizacion)
        self.actualizar_ventana()
        self.wids['b_guardar'].set_sensitive(False)
      

if __name__ == '__main__':
    v = CentrosDeTrabajo()

