import json
import random
import string
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from threading import Thread
import time

# ========================= MODELOS DE DOMINIO =========================

class Coche:
    """Clase que representa un vehículo"""
    def __init__(self, matricula, es_minusvalido=False, es_electrico=False):
        self.matricula = matricula
        self.es_minusvalido = es_minusvalido
        self.es_electrico = es_electrico
    
    def to_dict(self):
        return {
            'matricula': self.matricula,
            'es_minusvalido': self.es_minusvalido,
            'es_electrico': self.es_electrico
        }
    
    @staticmethod
    def from_dict(data):
        return Coche(
            data['matricula'], 
            data.get('es_minusvalido', False),
            data.get('es_electrico', False)
        )

class TipoPlaza:
    """Enumeración de tipos de plaza"""
    NORMAL = "normal"
    MINUSVALIDO = "minusvalido"
    ELECTRICO = "electrico"

class Aparcamiento:
    """Clase que representa una plaza de aparcamiento"""
    def __init__(self, id_aparcamiento, fila, columna, tipo=TipoPlaza.NORMAL):
        self.id = id_aparcamiento
        self.fila = fila
        self.columna = columna
        self.tipo = tipo
        self.ocupado = False
        self.coche = None
        self.timestamp_entrada = None
    
    def puede_ocupar(self, coche):
        """Verifica si un coche puede ocupar esta plaza"""
        if self.ocupado:
            return False
        
        # Plaza de minusválidos solo para coches con tarjeta
        if self.tipo == TipoPlaza.MINUSVALIDO and not coche.es_minusvalido:
            return False
        
        # Plaza eléctrica solo para coches eléctricos
        if self.tipo == TipoPlaza.ELECTRICO and not coche.es_electrico:
            return False
        
        return True
    
    def ocupar(self, coche):
        """Ocupa el aparcamiento con un coche"""
        if self.puede_ocupar(coche):
            self.ocupado = True
            self.coche = coche
            self.timestamp_entrada = datetime.now()
            return True
        return False
    
    def liberar(self):
        """Libera el aparcamiento"""
        coche = self.coche
        tiempo_estacionado = None
        if self.timestamp_entrada:
            tiempo_estacionado = datetime.now() - self.timestamp_entrada
        
        self.ocupado = False
        self.coche = None
        self.timestamp_entrada = None
        return coche, tiempo_estacionado
    
    def to_dict(self):
        return {
            'id': self.id,
            'fila': self.fila,
            'columna': self.columna,
            'tipo': self.tipo,
            'ocupado': self.ocupado,
            'coche': self.coche.to_dict() if self.coche else None,
            'timestamp_entrada': self.timestamp_entrada.isoformat() if self.timestamp_entrada else None
        }
    
    @staticmethod
    def from_dict(data):
        aparcamiento = Aparcamiento(
            data['id'], 
            data['fila'], 
            data['columna'], 
            data.get('tipo', TipoPlaza.NORMAL)
        )
        aparcamiento.ocupado = data['ocupado']
        if data['coche']:
            aparcamiento.coche = Coche.from_dict(data['coche'])
        if data['timestamp_entrada']:
            aparcamiento.timestamp_entrada = datetime.fromisoformat(data['timestamp_entrada'])
        return aparcamiento

# ========================= ESTRATEGIAS DE TARIFA =========================

class EstrategiaTarifa(ABC):
    """Clase abstracta para estrategias de tarificación"""
    
    @abstractmethod
    def calcular(self, tiempo_estacionado, coche, tipo_plaza):
        """Calcula la tarifa según el tiempo y características"""
        pass
    
    @abstractmethod
    def get_nombre(self):
        """Retorna el nombre de la estrategia"""
        pass

class TarifaEstandar(EstrategiaTarifa):
    """Tarifa estándar: 1.5€ por 20 segundos después de 30s gratis"""
    TIEMPO_GRATIS_SEGUNDOS = 30
    TARIFA_POR_SEGUNDO = 1.5 / 20
    
    def calcular(self, tiempo_estacionado, coche, tipo_plaza):
        if tiempo_estacionado is None:
            return 0
        
        segundos_totales = tiempo_estacionado.total_seconds()
        
        if segundos_totales <= self.TIEMPO_GRATIS_SEGUNDOS:
            return 0
        
        segundos_cobrables = segundos_totales - self.TIEMPO_GRATIS_SEGUNDOS
        tarifa = segundos_cobrables * self.TARIFA_POR_SEGUNDO
        
        return round(tarifa, 2)
    
    def get_nombre(self):
        return "Estándar"

class TarifaPorTramos(EstrategiaTarifa):
    """Tarifa por tramos horarios: más cara en horas punta"""
    TIEMPO_GRATIS_SEGUNDOS = 30
    
    def calcular(self, tiempo_estacionado, coche, tipo_plaza):
        if tiempo_estacionado is None:
            return 0
        
        segundos_totales = tiempo_estacionado.total_seconds()
        
        if segundos_totales <= self.TIEMPO_GRATIS_SEGUNDOS:
            return 0
        
        # Simular hora punta (entre 8-20h) con tarifa más alta
        hora_actual = datetime.now().hour
        if 8 <= hora_actual < 20:
            tarifa_por_segundo = 2.0 / 20  # Hora punta
        else:
            tarifa_por_segundo = 1.0 / 20  # Hora valle
        
        segundos_cobrables = segundos_totales - self.TIEMPO_GRATIS_SEGUNDOS
        tarifa = segundos_cobrables * tarifa_por_segundo
        
        return round(tarifa, 2)
    
    def get_nombre(self):
        return "Por Tramos"

class TarifaDiferenciada(EstrategiaTarifa):
    """Tarifa diferenciada: descuento para minusválidos, recargo para eléctricos"""
    TIEMPO_GRATIS_SEGUNDOS = 30
    TARIFA_BASE = 1.5 / 20
    
    def calcular(self, tiempo_estacionado, coche, tipo_plaza):
        if tiempo_estacionado is None:
            return 0
        
        segundos_totales = tiempo_estacionado.total_seconds()
        
        if segundos_totales <= self.TIEMPO_GRATIS_SEGUNDOS:
            return 0
        
        segundos_cobrables = segundos_totales - self.TIEMPO_GRATIS_SEGUNDOS
        tarifa = segundos_cobrables * self.TARIFA_BASE
        
        # Descuento 50% para minusválidos
        if coche.es_minusvalido:
            tarifa *= 0.5
        
        # Recargo por carga eléctrica
        if coche.es_electrico and tipo_plaza == TipoPlaza.ELECTRICO:
            tarifa += 2.0  # Coste de carga
        
        return round(tarifa, 2)
    
    def get_nombre(self):
        return "Diferenciada"

# ========================= CABINA =========================

class Cabina:
    """Clase que gestiona la generación de vehículos y tarifas"""
    MAX_INTENTOS_BUSQUEDA = 5
    
    def __init__(self, estrategia_tarifa=None):
        self.estrategia_tarifa = estrategia_tarifa or TarifaEstandar()
    
    def cambiar_estrategia_tarifa(self, estrategia):
        """Permite cambiar la estrategia de tarificación"""
        self.estrategia_tarifa = estrategia
    
    def generar_matricula(self):
        """Genera una matrícula aleatoria española"""
        numeros = ''.join(random.choices(string.digits, k=4))
        letras = ''.join(random.choices(string.ascii_uppercase, k=3))
        return f"{numeros}{letras}"
    
    def detectar_caracteristicas(self):
        """Detecta características del vehículo"""
        es_minusvalido = random.random() < 0.15  # 15%
        es_electrico = random.random() < 0.20     # 20%
        return es_minusvalido, es_electrico
    
    def calcular_tarifa(self, tiempo_estacionado, coche, tipo_plaza):
        """Calcula la tarifa usando la estrategia configurada"""
        return self.estrategia_tarifa.calcular(tiempo_estacionado, coche, tipo_plaza)

# ========================= PARKING (INTERFAZ PÚBLICA) =========================

class Parking:
    """Clase principal que gestiona el parking con interfaz pública"""
    
    def __init__(self, filas, columnas, config_plazas=None):
        self.aparcamientos = []
        self.cabina = Cabina()
        self.filas = filas
        self.columnas = columnas
        self._crear_aparcamientos(filas, columnas, config_plazas or {})
    
    def _crear_aparcamientos(self, filas, columnas, config):
        """Crea la estructura de aparcamientos"""
        letras_fila = string.ascii_uppercase[:filas]
        total_plazas = filas * columnas
        
        # Configuración por defecto
        porcentaje_minusvalidos = config.get('minusvalidos', 0.15)
        porcentaje_electricos = config.get('electricos', 0.10)
        
        num_minusvalidos = int(total_plazas * porcentaje_minusvalidos)
        num_electricos = int(total_plazas * porcentaje_electricos)
        
        # Crear todas las plazas
        todas_plazas = []
        for letra in letras_fila:
            for col in range(1, columnas + 1):
                id_aparcamiento = f"{letra}{col}"
                todas_plazas.append((id_aparcamiento, letra, col))
        
        # Asignar tipos de plaza
        plazas_especiales = random.sample(todas_plazas, num_minusvalidos + num_electricos)
        plazas_minusvalidos = plazas_especiales[:num_minusvalidos]
        plazas_electricos = plazas_especiales[num_minusvalidos:]
        
        for id_aparcamiento, letra, col in todas_plazas:
            if (id_aparcamiento, letra, col) in plazas_minusvalidos:
                tipo = TipoPlaza.MINUSVALIDO
            elif (id_aparcamiento, letra, col) in plazas_electricos:
                tipo = TipoPlaza.ELECTRICO
            else:
                tipo = TipoPlaza.NORMAL
            
            aparcamiento = Aparcamiento(id_aparcamiento, letra, col, tipo)
            self.aparcamientos.append(aparcamiento)
    
    # ========== INTERFAZ PÚBLICA ==========
    
    def entrar(self, matricula=None, es_minusvalido=False, es_electrico=False):
        """
        Procesa la entrada de un vehículo al parking.
        
        Args:
            matricula: Matrícula del vehículo (opcional, se genera si no se proporciona)
            es_minusvalido: Si el vehículo tiene tarjeta de minusválido
            es_electrico: Si el vehículo es eléctrico
        
        Returns:
            tuple: (éxito: bool, mensaje: str, plaza_id: str|None)
        """
        if matricula is None:
            matricula = self.cabina.generar_matricula()
            es_minusvalido, es_electrico = self.cabina.detectar_caracteristicas()
        
        coche = Coche(matricula, es_minusvalido, es_electrico)
        
        # Buscar plaza adecuada
        for _ in range(self.cabina.MAX_INTENTOS_BUSQUEDA):
            aparcamiento = random.choice(self.aparcamientos)
            
            if aparcamiento.puede_ocupar(coche):
                aparcamiento.ocupar(coche)
                tipo_texto = self._get_tipo_vehiculo_texto(coche)
                return True, f"Vehículo {matricula} ({tipo_texto}) estacionado", aparcamiento.id
        
        return False, f"No hay plazas disponibles para {matricula}", None
    
    def salir(self, matricula):
        """
        Procesa la salida de un vehículo del parking.
        
        Args:
            matricula: Matrícula del vehículo a salir
        
        Returns:
            tuple: (éxito: bool, mensaje: str, tarifa: float)
        """
        aparcamiento = self._buscar_por_matricula(matricula)
        
        if not aparcamiento:
            return False, f"Vehículo {matricula} no encontrado", 0
        
        coche, tiempo = aparcamiento.liberar()
        tarifa = self.cabina.calcular_tarifa(tiempo, coche, aparcamiento.tipo)
        
        segundos = tiempo.total_seconds() if tiempo else 0
        return True, f"Tiempo: {segundos:.0f}s - Tarifa: {tarifa}€", tarifa
    
    def listar_coches(self):
        """
        Lista todos los coches actualmente estacionados.
        
        Returns:
            list: Lista de diccionarios con info de cada coche
        """
        coches = []
        for aparcamiento in self.aparcamientos:
            if aparcamiento.ocupado:
                tiempo = (datetime.now() - aparcamiento.timestamp_entrada).total_seconds()
                coches.append({
                    'matricula': aparcamiento.coche.matricula,
                    'plaza': aparcamiento.id,
                    'tipo_plaza': aparcamiento.tipo,
                    'es_minusvalido': aparcamiento.coche.es_minusvalido,
                    'es_electrico': aparcamiento.coche.es_electrico,
                    'tiempo_segundos': round(tiempo, 1)
                })
        return coches
    
    def plazas_libres(self, tipo=None):
        """
        Retorna el número de plazas libres.
        
        Args:
            tipo: Tipo de plaza a filtrar (opcional)
        
        Returns:
            int: Número de plazas libres
        """
        libres = [a for a in self.aparcamientos if not a.ocupado]
        if tipo:
            libres = [a for a in libres if a.tipo == tipo]
        return len(libres)
    
    def resumen(self):
        """
        Retorna un resumen del estado del parking.
        
        Returns:
            dict: Diccionario con información resumida
        """
        total = len(self.aparcamientos)
        ocupadas = sum(1 for a in self.aparcamientos if a.ocupado)
        
        por_tipo = {}
        for tipo in [TipoPlaza.NORMAL, TipoPlaza.MINUSVALIDO, TipoPlaza.ELECTRICO]:
            total_tipo = sum(1 for a in self.aparcamientos if a.tipo == tipo)
            ocupadas_tipo = sum(1 for a in self.aparcamientos if a.tipo == tipo and a.ocupado)
            por_tipo[tipo] = {
                'total': total_tipo,
                'ocupadas': ocupadas_tipo,
                'libres': total_tipo - ocupadas_tipo
            }
        
        return {
            'total_plazas': total,
            'ocupadas': ocupadas,
            'libres': total - ocupadas,
            'ocupacion_porcentaje': (ocupadas / total * 100) if total > 0 else 0,
            'por_tipo': por_tipo,
            'estrategia_tarifa': self.cabina.estrategia_tarifa.get_nombre()
        }
    
    def cambiar_tarifa(self, estrategia):
        """
        Cambia la estrategia de tarificación.
        
        Args:
            estrategia: Nueva estrategia de tarifa
        """
        self.cabina.cambiar_estrategia_tarifa(estrategia)
    
    # ========== MÉTODOS DE SOPORTE ==========
    
    def _buscar_por_matricula(self, matricula):
        """Busca un aparcamiento por matrícula del coche"""
        for aparcamiento in self.aparcamientos:
            if aparcamiento.ocupado and aparcamiento.coche.matricula == matricula:
                return aparcamiento
        return None
    
    def _get_tipo_vehiculo_texto(self, coche):
        """Retorna descripción del tipo de vehículo"""
        tipos = []
        if coche.es_minusvalido:
            tipos.append("PMR")
        if coche.es_electrico:
            tipos.append("EV")
        return ", ".join(tipos) if tipos else "Normal"
    
    # ========== PERSISTENCIA ==========
    
    def guardar_estado(self, archivo='parking_estado.json'):
        """Guarda el estado del parking en JSON"""
        datos = {
            'filas': self.filas,
            'columnas': self.columnas,
            'aparcamientos': [a.to_dict() for a in self.aparcamientos],
            'estrategia_tarifa': self.cabina.estrategia_tarifa.get_nombre()
        }
        with open(archivo, 'w') as f:
            json.dump(datos, f, indent=2)
    
    @staticmethod
    def cargar_estado(archivo='parking_estado.json'):
        """Carga el estado del parking desde JSON"""
        try:
            with open(archivo, 'r') as f:
                datos = json.load(f)
            
            parking = Parking(datos['filas'], datos['columnas'])
            parking.aparcamientos = [Aparcamiento.from_dict(a) for a in datos['aparcamientos']]
            
            # Restaurar estrategia de tarifa
            nombre_estrategia = datos.get('estrategia_tarifa', 'Estándar')
            if nombre_estrategia == 'Por Tramos':
                parking.cambiar_tarifa(TarifaPorTramos())
            elif nombre_estrategia == 'Diferenciada':
                parking.cambiar_tarifa(TarifaDiferenciada())
            
            return parking
        except FileNotFoundError:
            return None

# ========================= INTERFAZ GRÁFICA =========================

class InterfazParking:
    """Interfaz gráfica mejorada del parking"""
    
    def __init__(self, parking):
        self.parking = parking
        self.automatico = False
        
        self.ventana = tk.Tk()
        self.ventana.title("Sistema de Parking Inteligente")
        self.ventana.geometry("1600x950")
        self.ventana.configure(bg='#f0f0f0')
        
        self._crear_interfaz()
        
        # Hilo automático
        self.hilo_automatico = Thread(target=self.proceso_automatico, daemon=True)
        self.hilo_automatico.start()
    
    def _crear_interfaz(self):
        """Crea todos los elementos de la interfaz"""
        # Panel superior - Controles
        frame_superior = tk.Frame(self.ventana, bg='#2c3e50', height=120)
        frame_superior.pack(fill=tk.X, padx=10, pady=5)
        frame_superior.pack_propagate(False)
        
        # Título
        tk.Label(frame_superior, text="🅿️ SISTEMA DE PARKING INTELIGENTE", 
                font=('Arial', 18, 'bold'), bg='#2c3e50', fg='white').pack(pady=5)
        
        # Botones
        frame_botones = tk.Frame(frame_superior, bg='#2c3e50')
        frame_botones.pack(pady=5)
        
        botones = [
            ("🚗 Entrada Automática", self.entrada_automatica, '#27ae60'),
            ("🔍 Entrada Manual", self.entrada_manual, '#3498db'),
            ("🚪 Salir Vehículo", self.salir_vehiculo, '#e74c3c'),
            ("📊 Listar Coches", self.mostrar_lista_coches, '#9b59b6'),
            ("💰 Cambiar Tarifa", self.cambiar_tarifa, '#f39c12'),
            ("💾 Guardar", self.guardar_estado, '#16a085')
        ]
        
        for texto, comando, color in botones:
            tk.Button(frame_botones, text=texto, command=comando, 
                     bg=color, fg='white', font=('Arial', 10, 'bold'),
                     width=18, height=2).pack(side=tk.LEFT, padx=3)
        
        self.boton_automatico = tk.Button(frame_botones, text="▶️ Automático", 
                                         command=self.toggle_automatico,
                                         bg='#8e44ad', fg='white', 
                                         font=('Arial', 10, 'bold'),
                                         width=18, height=2)
        self.boton_automatico.pack(side=tk.LEFT, padx=3)
        
        # Panel de información
        frame_info = tk.Frame(self.ventana, bg='#ecf0f1', height=50)
        frame_info.pack(fill=tk.X, padx=10, pady=5)
        
        self.label_info = tk.Label(frame_info, text="", font=('Arial', 11), 
                                   bg='#ecf0f1', fg='#2c3e50')
        self.label_info.pack(pady=10)
        
        # Canvas para el parking
        self.canvas = tk.Canvas(self.ventana, bg='white', highlightthickness=2, 
                               highlightbackground='#bdc3c7')
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.actualizar_vista()
    
    def actualizar_vista(self):
        """Actualiza la visualización del parking"""
        self.canvas.delete("all")
        
        resumen = self.parking.resumen()
        
        # Información superior
        info_texto = (f"Ocupación: {resumen['ocupacion_porcentaje']:.1f}% "
                     f"({resumen['ocupadas']}/{resumen['total_plazas']}) | "
                     f"Tarifa: {resumen['estrategia_tarifa']} | "
                     f"Libres: Normal({resumen['por_tipo'][TipoPlaza.NORMAL]['libres']}) "
                     f"PMR({resumen['por_tipo'][TipoPlaza.MINUSVALIDO]['libres']}) "
                     f"EV({resumen['por_tipo'][TipoPlaza.ELECTRICO]['libres']})")
        
        self.label_info.config(text=info_texto)
        
        # Configuración visual
        ancho_plaza = 90
        alto_plaza = 65
        margen_x = 50
        espacio_x = 8
        espacio_y = 8
        
        # Organizar plazas
        filas_dict = {}
        for aparcamiento in self.parking.aparcamientos:
            if aparcamiento.fila not in filas_dict:
                filas_dict[aparcamiento.fila] = []
            filas_dict[aparcamiento.fila].append(aparcamiento)
        
        filas_ordenadas = sorted(filas_dict.keys())
        for fila in filas_ordenadas:
            filas_dict[fila].sort(key=lambda a: a.columna)
        
        # Dibujar desde abajo
        canvas_height = self.canvas.winfo_height() or 700
        y_inicial = canvas_height - 150
        
        colores_tipo = {
            TipoPlaza.NORMAL: '#2ecc71',
            TipoPlaza.MINUSVALIDO: '#3498db',
            TipoPlaza.ELECTRICO: '#f1c40f'
        }
        
        simbolos_tipo = {
            TipoPlaza.NORMAL: '',
            TipoPlaza.MINUSVALIDO: '♿',
            TipoPlaza.ELECTRICO: '⚡'
        }
        
        for idx, fila in enumerate(reversed(filas_ordenadas)):
            y_actual = y_inicial - ((idx + 1) * (alto_plaza + espacio_y))
            x_actual = margen_x
            
            for aparcamiento in filas_dict[fila]:
                # Color según estado
                if aparcamiento.ocupado:
                    color = '#e74c3c'
                else:
                    color = colores_tipo[aparcamiento.tipo]
                
                # Dibujar plaza
                self.canvas.create_rectangle(
                    x_actual, y_actual,
                    x_actual + ancho_plaza, y_actual + alto_plaza,
                    fill=color, outline='#34495e', width=2
                )
                
                # ID
                self.canvas.create_text(
                    x_actual + ancho_plaza/2, y_actual + 15,
                    text=aparcamiento.id, font=('Arial', 10, 'bold'),
                    fill='white' if aparcamiento.ocupado else 'black'
                )
                
                # Matrícula o símbolo
                if aparcamiento.ocupado:
                    self.canvas.create_text(
                        x_actual + ancho_plaza/2, y_actual + 35,
                        text=aparcamiento.coche.matricula, 
                        font=('Arial', 8), fill='white'
                    )
                    # Indicadores
                    indicadores = []
                    if aparcamiento.coche.es_minusvalido:
                        indicadores.append('♿')
                    if aparcamiento.coche.es_electrico:
                        indicadores.append('⚡')
                    if indicadores:
                        self.canvas.create_text(
                            x_actual + ancho_plaza/2, y_actual + 52,
                            text=' '.join(indicadores), font=('Arial', 10),
                            fill='white'
                        )
                else:
                    simbolo = simbolos_tipo[aparcamiento.tipo]
                    if simbolo:
                        self.canvas.create_text(
                            x_actual + ancho_plaza/2, y_actual + 45,
                            text=simbolo, font=('Arial', 16)
                        )
                
                x_actual += ancho_plaza + espacio_x
        
        # Cabina
        total_ancho = self.parking.columnas * (ancho_plaza + espacio_x)
        cabina_x = margen_x + (total_ancho / 2) - 60
        cabina_y = y_inicial + 30
        
        self.canvas.create_rectangle(
            cabina_x, cabina_y, cabina_x + 120, cabina_y + 60,
            fill='#f39c12', outline='#34495e', width=3
        )
        self.canvas.create_text(
            cabina_x + 60, cabina_y + 30,
            text="🎫 CABINA", font=('Arial', 12, 'bold'), fill='white'
        )
    
    def entrada_automatica(self):
        """Entrada con matrícula generada automáticamente"""
        exito, mensaje, plaza = self.parking.entrar()
        if exito:
            messagebox.showinfo("✅ Entrada", f"{mensaje}\nPlaza: {plaza}")
        else:
            messagebox.showwarning("⚠️ Sin Plaza", mensaje)
        self.actualizar_vista()
    
    def entrada_manual(self):
        """Entrada con datos introducidos manualmente"""
        ventana = tk.Toplevel(self.ventana)
        ventana.title("Entrada Manual")
        ventana.geometry("350x250")
        ventana.configure(bg='#ecf0f1')
        
        tk.Label(ventana, text="Matrícula:", bg='#ecf0f1', 
                font=('Arial', 10)).pack(pady=5)
        entry_matricula = tk.Entry(ventana, font=('Arial', 11))
        entry_matricula.pack(pady=5)
        
        var_minusvalido = tk.BooleanVar()
        tk.Checkbutton(ventana, text="♿ Tarjeta Minusválido", 
                      variable=var_minusvalido, bg='#ecf0f1',
                      font=('Arial', 10)).pack(pady=5)
        
        var_electrico = tk.BooleanVar()
        tk.Checkbutton(ventana, text="⚡ Vehículo Eléctrico", 
                      variable=var_electrico, bg='#ecf0f1',
                      font=('Arial', 10)).pack(pady=5)
        
        def confirmar():
            matricula = entry_matricula.get().upper().strip()
            if not matricula:
                messagebox.showerror("Error", "Introduce una matrícula")
                return
            
            exito, mensaje, plaza = self.parking.entrar(
                matricula, var_minusvalido.get(), var_electrico.get()
            )
            
            if exito:
                messagebox.showinfo("✅ Entrada", f"{mensaje}\nPlaza: {plaza}")
                ventana.destroy()
            else:
                messagebox.showwarning("⚠️ Sin Plaza", mensaje)
            
            self.actualizar_vista()
        
        tk.Button(ventana, text="Confirmar Entrada", command=confirmar,
                 bg='#27ae60', fg='white', font=('Arial', 11, 'bold'),
                 width=20).pack(pady=15)
    
    def salir_vehiculo(self):
        """Procesa la salida de un vehículo"""
        coches = self.parking.listar_coches()
        
        if not coches:
            messagebox.showinfo("Info", "No hay vehículos en el parking")
            return
        
        ventana = tk.Toplevel(self.ventana)
        ventana.title("Salida de Vehículo")
        ventana.geometry("400x300")
        ventana.configure(bg='#ecf0f1')
        
        tk.Label(ventana, text="Selecciona vehículo o introduce matrícula:", 
                bg='#ecf0f1', font=('Arial', 11, 'bold')).pack(pady=10)
        
        # Listbox con coches
        frame_lista = tk.Frame(ventana, bg='#ecf0f1')
        frame_lista.pack(pady=5)
        
        scrollbar = tk.Scrollbar(frame_lista)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        listbox = tk.Listbox(frame_lista, width=40, height=8, 
                            yscrollcommand=scrollbar.set,
                            font=('Courier', 9))
        listbox.pack(side=tk.LEFT)
        scrollbar.config(command=listbox.yview)
        
        for coche in coches:
            texto = f"{coche['matricula']:8} | Plaza: {coche['plaza']:3} | {coche['tiempo_segundos']:.0f}s"
            listbox.insert(tk.END, texto)
        
        tk.Label(ventana, text="O introduce matrícula:", 
                bg='#ecf0f1', font=('Arial', 10)).pack(pady=5)
        entry_matricula = tk.Entry(ventana, font=('Arial', 11))
        entry_matricula.pack(pady=5)
        
        def procesar_salida():
            # Primero intentar con selección
            seleccion = listbox.curselection()
            if seleccion:
                matricula = coches[seleccion[0]]['matricula']
            else:
                matricula = entry_matricula.get().upper().strip()
            
            if not matricula:
                messagebox.showerror("Error", "Selecciona un vehículo o introduce matrícula")
                return
            
            exito, mensaje, tarifa = self.parking.salir(matricula)
            
            if exito:
                messagebox.showinfo("✅ Salida Exitosa", 
                                  f"Vehículo: {matricula}\n{mensaje}")
                ventana.destroy()
            else:
                messagebox.showerror("❌ Error", mensaje)
            
            self.actualizar_vista()
        
        tk.Button(ventana, text="Procesar Salida", command=procesar_salida,
                 bg='#e74c3c', fg='white', font=('Arial', 11, 'bold'),
                 width=20).pack(pady=10)
    
    def mostrar_lista_coches(self):
        """Muestra lista completa de coches estacionados"""
        coches = self.parking.listar_coches()
        resumen = self.parking.resumen()
        
        ventana = tk.Toplevel(self.ventana)
        ventana.title("Vehículos Estacionados")
        ventana.geometry("700x500")
        ventana.configure(bg='#ecf0f1')
        
        # Resumen
        frame_resumen = tk.Frame(ventana, bg='#3498db')
        frame_resumen.pack(fill=tk.X, pady=5)
        
        texto_resumen = (f"Total: {resumen['ocupadas']}/{resumen['total_plazas']} "
                        f"({resumen['ocupacion_porcentaje']:.1f}%)")
        tk.Label(frame_resumen, text=texto_resumen, bg='#3498db', fg='white',
                font=('Arial', 12, 'bold')).pack(pady=10)
        
        # Tabla
        frame_tabla = tk.Frame(ventana)
        frame_tabla.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        columns = ('Matrícula', 'Plaza', 'Tipo Plaza', 'PMR', 'EV', 'Tiempo (s)')
        tree = ttk.Treeview(frame_tabla, columns=columns, show='headings', height=15)
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100, anchor='center')
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(frame_tabla, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Datos
        for coche in coches:
            tree.insert('', tk.END, values=(
                coche['matricula'],
                coche['plaza'],
                coche['tipo_plaza'],
                '✓' if coche['es_minusvalido'] else '',
                '✓' if coche['es_electrico'] else '',
                f"{coche['tiempo_segundos']:.1f}"
            ))
    
    def cambiar_tarifa(self):
        """Permite cambiar la estrategia de tarificación"""
        ventana = tk.Toplevel(self.ventana)
        ventana.title("Cambiar Estrategia de Tarifa")
        ventana.geometry("400x300")
        ventana.configure(bg='#ecf0f1')
        
        tk.Label(ventana, text="Selecciona estrategia de tarifa:", 
                bg='#ecf0f1', font=('Arial', 12, 'bold')).pack(pady=15)
        
        var_estrategia = tk.StringVar(value=self.parking.resumen()['estrategia_tarifa'])
        
        estrategias = [
            ('Estándar', TarifaEstandar(), 
             '1.5€ por 20s después de 30s gratis'),
            ('Por Tramos', TarifaPorTramos(), 
             'Más cara en horas punta (8-20h)'),
            ('Diferenciada', TarifaDiferenciada(), 
             '50% desc. PMR, +2€ carga eléctrica')
        ]
        
        for nombre, estrategia, descripcion in estrategias:
            frame = tk.Frame(ventana, bg='#ecf0f1')
            frame.pack(pady=5, padx=20, fill=tk.X)
            
            tk.Radiobutton(frame, text=nombre, variable=var_estrategia, 
                          value=nombre, bg='#ecf0f1',
                          font=('Arial', 11, 'bold')).pack(anchor=tk.W)
            tk.Label(frame, text=descripcion, bg='#ecf0f1',
                    font=('Arial', 9), fg='#7f8c8d').pack(anchor=tk.W, padx=20)
        
        def aplicar():
            seleccion = var_estrategia.get()
            for nombre, estrategia, _ in estrategias:
                if nombre == seleccion:
                    self.parking.cambiar_tarifa(estrategia)
                    messagebox.showinfo("✅ Actualizado", 
                                      f"Tarifa cambiada a: {nombre}")
                    ventana.destroy()
                    self.actualizar_vista()
                    break
        
        tk.Button(ventana, text="Aplicar", command=aplicar,
                 bg='#f39c12', fg='white', font=('Arial', 11, 'bold'),
                 width=15).pack(pady=20)
    
    def toggle_automatico(self):
        """Activa/desactiva el modo automático"""
        self.automatico = not self.automatico
        if self.automatico:
            self.boton_automatico.config(text="⏸️ Pausar", bg='#c0392b')
        else:
            self.boton_automatico.config(text="▶️ Automático", bg='#8e44ad')
    
    def proceso_automatico(self):
        """Proceso que simula entradas y salidas automáticas"""
        while True:
            if self.automatico:
                # Entrada aleatoria
                if random.random() < 0.6:
                    self.parking.entrar()
                    self.ventana.after(0, self.actualizar_vista)
                
                time.sleep(random.uniform(2, 5))
                
                # Salida aleatoria
                if random.random() < 0.4 and self.automatico:
                    coches = self.parking.listar_coches()
                    if coches:
                        coche = random.choice(coches)
                        self.parking.salir(coche['matricula'])
                        self.ventana.after(0, self.actualizar_vista)
            
            time.sleep(1)
    
    def guardar_estado(self):
        """Guarda el estado del parking"""
        self.parking.guardar_estado()
        messagebox.showinfo("💾 Guardado", "Estado guardado correctamente")
    
    def iniciar(self):
        """Inicia la interfaz gráfica"""
        self.ventana.mainloop()

# ========================= PROGRAMA PRINCIPAL =========================

if __name__ == "__main__":
    # Intentar cargar estado previo
    parking = Parking.cargar_estado()
    
    # Si no existe, crear uno nuevo
    if parking is None:
        print("Creando nuevo parking...")
        config = {
            'minusvalidos': 0.15,  # 15% plazas minusválidos
            'electricos': 0.10      # 10% plazas eléctricas
        }
        parking = Parking(filas=7, columnas=13, config_plazas=config)
    
    interfaz = InterfazParking(parking)
    interfaz.iniciar()