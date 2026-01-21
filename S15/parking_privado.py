import json
import random
import string
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import messagebox, simpledialog
import logging
from threading import Thread
import time

# Configurar logging
logging.basicConfig(
    filename='parking.log',
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

class Coche:
    """Clase que representa un vehículo"""
    def __init__(self, matricula, es_minusvalido=False):
        self.matricula = matricula
        self.es_minusvalido = es_minusvalido
    
    def to_dict(self):
        return {
            'matricula': self.matricula,
            'es_minusvalido': self.es_minusvalido
        }
    
    @staticmethod
    def from_dict(data):
        return Coche(data['matricula'], data['es_minusvalido'])

class Aparcamiento:
    """Clase que representa una plaza de aparcamiento"""
    def __init__(self, id_aparcamiento, fila, columna, solo_minusvalidos=False):
        self.id = id_aparcamiento
        self.fila = fila
        self.columna = columna
        self.solo_minusvalidos = solo_minusvalidos
        self.ocupado = False
        self.coche = None
        self.timestamp_entrada = None
    
    def puede_ocupar(self, coche):
        """Verifica si un coche puede ocupar esta plaza"""
        if self.ocupado:
            return False
        if self.solo_minusvalidos and not coche.es_minusvalido:
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
            'solo_minusvalidos': self.solo_minusvalidos,
            'ocupado': self.ocupado,
            'coche': self.coche.to_dict() if self.coche else None,
            'timestamp_entrada': self.timestamp_entrada.isoformat() if self.timestamp_entrada else None
        }
    
    @staticmethod
    def from_dict(data):
        aparcamiento = Aparcamiento(data['id'], data['fila'], data['columna'], data.get('solo_minusvalidos', False))
        aparcamiento.ocupado = data['ocupado']
        if data['coche']:
            aparcamiento.coche = Coche.from_dict(data['coche'])
        if data['timestamp_entrada']:
            aparcamiento.timestamp_entrada = datetime.fromisoformat(data['timestamp_entrada'])
        return aparcamiento

class Cabina:
    """Clase que gestiona la entrada y salida de vehículos"""
    TIEMPO_GRATIS_SEGUNDOS = 30
    TARIFA_POR_SEGUNDO = 1.5 / 20  # 1.5€ por 20 segundos
    MAX_INTENTOS_BUSQUEDA = 5
    
    def __init__(self):
        pass
    
    def generar_matricula(self):
        """Genera una matrícula aleatoria española"""
        numeros = ''.join(random.choices(string.digits, k=4))
        letras = ''.join(random.choices(string.ascii_uppercase, k=3))
        return f"{numeros}{letras}"
    
    def detectar_minusvalido(self):
        """Simula la detección de si el vehículo tiene ocupantes minusválidos"""
        return random.random() < 0.15  # 15% de probabilidad
    
    def calcular_tarifa(self, tiempo_estacionado):
        """Calcula la tarifa según el tiempo estacionado"""
        if tiempo_estacionado is None:
            return 0
        
        segundos_totales = tiempo_estacionado.total_seconds()
        
        if segundos_totales <= self.TIEMPO_GRATIS_SEGUNDOS:
            return 0
        
        segundos_cobrables = segundos_totales - self.TIEMPO_GRATIS_SEGUNDOS
        tarifa = segundos_cobrables * self.TARIFA_POR_SEGUNDO
        
        return round(tarifa, 2)
    
    def procesar_entrada(self, parking):
        """Procesa la entrada de un vehículo al parking"""
        matricula = self.generar_matricula()
        es_minusvalido = self.detectar_minusvalido()
        coche = Coche(matricula, es_minusvalido)
        
        tipo_vehiculo = "MINUSVÁLIDO" if es_minusvalido else "NORMAL"
        logging.info(f"INTENTO DE ENTRADA - Vehículo {matricula} ({tipo_vehiculo}) intenta acceder al parking")
        
        # Buscar plaza aleatoriamente con máximo de intentos
        aparcamiento_asignado = None
        for intento in range(1, self.MAX_INTENTOS_BUSQUEDA + 1):
            aparcamiento = random.choice(parking.aparcamientos)
            
            if aparcamiento.puede_ocupar(coche):
                aparcamiento.ocupar(coche)
                aparcamiento_asignado = aparcamiento
                logging.info(f"ENTRADA EXITOSA - Vehículo {matricula} estacionado en plaza {aparcamiento.id} (intento {intento})")
                return True, f"Vehículo {matricula} estacionado en {aparcamiento.id}"
            else:
                motivo = "ocupada" if aparcamiento.ocupado else "solo minusválidos"
                logging.info(f"Intento {intento} - Plaza {aparcamiento.id} no disponible ({motivo})")
        
        logging.warning(f"ENTRADA RECHAZADA - Vehículo {matricula} no encontró plaza tras {self.MAX_INTENTOS_BUSQUEDA} intentos")
        return False, f"Vehículo {matricula} no encontró plaza y se fue"
    
    def procesar_salida(self, parking, id_aparcamiento=None):
        """Procesa la salida de un vehículo del parking"""
        # Si no se especifica ID, elegir uno ocupado al azar
        if id_aparcamiento is None:
            aparcamientos_ocupados = [a for a in parking.aparcamientos if a.ocupado]
            if not aparcamientos_ocupados:
                logging.warning("SALIDA FALLIDA - No hay vehículos en el parking")
                return False, "No hay vehículos para salir"
            aparcamiento = random.choice(aparcamientos_ocupados)
        else:
            aparcamiento = parking.buscar_aparcamiento_por_id(id_aparcamiento)
        
        if aparcamiento and aparcamiento.ocupado:
            coche, tiempo_estacionado = aparcamiento.liberar()
            tarifa = self.calcular_tarifa(tiempo_estacionado)
            
            segundos = tiempo_estacionado.total_seconds() if tiempo_estacionado else 0
            
            logging.info(f"SALIDA - Vehículo {coche.matricula} sale de plaza {aparcamiento.id} - Tiempo: {segundos:.1f}s - Tarifa: {tarifa}€")
            return True, f"Vehículo {coche.matricula} - Tiempo: {segundos:.1f}s - Tarifa: {tarifa}€"
        else:
            logging.warning(f"SALIDA FALLIDA - Plaza {id_aparcamiento if id_aparcamiento else 'aleatoria'} no está ocupada")
            return False, "El aparcamiento no está ocupado"

class Parking:
    """Clase principal que gestiona el parking"""
    def __init__(self, filas, columnas, porcentaje_minusvalidos=0.1):
        self.aparcamientos = []
        self.cabina = Cabina()
        self.filas = filas
        self.columnas = columnas
        self._crear_aparcamientos(filas, columnas, porcentaje_minusvalidos)
        logging.info(f"SISTEMA INICIADO - Parking creado con {len(self.aparcamientos)} plazas ({filas}x{columnas})")
    
    def _crear_aparcamientos(self, filas, columnas, porcentaje_minusvalidos):
        """Crea la estructura de aparcamientos"""
        letras_fila = string.ascii_uppercase[:filas]
        total_plazas = filas * columnas
        num_minusvalidos = int(total_plazas * porcentaje_minusvalidos)
        
        # Crear todas las plazas
        todas_plazas = []
        for i, letra in enumerate(letras_fila):
            for col in range(1, columnas + 1):
                id_aparcamiento = f"{letra}{col}"
                todas_plazas.append((id_aparcamiento, letra, col))
        
        # Seleccionar aleatoriamente cuáles serán para minusválidos
        plazas_minusvalidos = random.sample(todas_plazas, num_minusvalidos)
        
        for id_aparcamiento, letra, col in todas_plazas:
            solo_minusvalidos = (id_aparcamiento, letra, col) in plazas_minusvalidos
            aparcamiento = Aparcamiento(id_aparcamiento, letra, col, solo_minusvalidos)
            self.aparcamientos.append(aparcamiento)
            
            if solo_minusvalidos:
                logging.info(f"Plaza {id_aparcamiento} configurada como EXCLUSIVA para minusválidos")
    
    def buscar_aparcamiento_por_id(self, id_aparcamiento):
        """Busca un aparcamiento por su ID"""
        for aparcamiento in self.aparcamientos:
            if aparcamiento.id == id_aparcamiento:
                return aparcamiento
        return None
    
    def obtener_ocupacion(self):
        """Retorna el porcentaje de ocupación"""
        ocupados = sum(1 for a in self.aparcamientos if a.ocupado)
        total = len(self.aparcamientos)
        return (ocupados / total) * 100 if total > 0 else 0
    
    def guardar_estado(self, archivo='parking_estado.json'):
        """Guarda el estado del parking en un archivo JSON"""
        datos = {
            'filas': self.filas,
            'columnas': self.columnas,
            'aparcamientos': [a.to_dict() for a in self.aparcamientos]
        }
        with open(archivo, 'w') as f:
            json.dump(datos, f, indent=2)
        logging.info("Estado del parking guardado en JSON")
    
    @staticmethod
    def cargar_estado(archivo='parking_estado.json'):
        """Carga el estado del parking desde un archivo JSON"""
        try:
            with open(archivo, 'r') as f:
                datos = json.load(f)
            
            parking = Parking(datos['filas'], datos['columnas'], 0)
            parking.aparcamientos = [Aparcamiento.from_dict(a) for a in datos['aparcamientos']]
            logging.info("Estado del parking cargado desde JSON")
            return parking
        except FileNotFoundError:
            return None

class InterfazParking:
    """Interfaz gráfica simple del parking"""
    def __init__(self, parking):
        self.parking = parking
        self.automatico = False
        self.ventana = tk.Tk()
        self.ventana.title("Sistema de Parking Automático")
        self.ventana.geometry("1500x900")
        
        self.canvas = tk.Canvas(self.ventana, width=1400, height=800, bg='white')
        self.canvas.pack(pady=10)
        
        self.frame_botones = tk.Frame(self.ventana)
        self.frame_botones.pack(pady=10)
        
        tk.Button(self.frame_botones, text="Entrada Manual", command=self.entrada_vehiculo, 
                 bg='green', fg='white', font=('Arial', 11)).pack(side=tk.LEFT, padx=5)
        
        tk.Button(self.frame_botones, text="Salida Manual", command=self.salida_vehiculo,
                 bg='red', fg='white', font=('Arial', 11)).pack(side=tk.LEFT, padx=5)
        
        self.boton_automatico = tk.Button(self.frame_botones, text="Iniciar Automático", 
                                         command=self.toggle_automatico,
                                         bg='purple', fg='white', font=('Arial', 11))
        self.boton_automatico.pack(side=tk.LEFT, padx=5)
        
        tk.Button(self.frame_botones, text="Guardar Estado", command=self.guardar_estado,
                 bg='orange', fg='white', font=('Arial', 11)).pack(side=tk.LEFT, padx=5)
        
        self.label_info = tk.Label(self.ventana, text="", font=('Arial', 10))
        self.label_info.pack()
        
        self.dibujar_parking()
        
        # Iniciar hilo automático
        self.hilo_automatico = Thread(target=self.proceso_automatico, daemon=True)
        self.hilo_automatico.start()
    
    def dibujar_parking(self):
        """Dibuja el estado actual del parking desde abajo hacia arriba"""
        self.canvas.delete("all")
        
        ancho_plaza = 100
        alto_plaza = 70
        margen_x = 50
        espacio_x = 10
        espacio_y = 10
        
        ocupacion = self.parking.obtener_ocupacion()
        total_plazas = len(self.parking.aparcamientos)
        ocupadas = sum(1 for a in self.parking.aparcamientos if a.ocupado)
        minusvalidos_total = sum(1 for a in self.parking.aparcamientos if a.solo_minusvalidos)
        
        self.label_info.config(
            text=f"Ocupación: {ocupacion:.1f}% ({ocupadas}/{total_plazas}) - Plazas minusválidos: {minusvalidos_total}"
        )
        
        # Organizar por filas
        filas_dict = {}
        for aparcamiento in self.parking.aparcamientos:
            if aparcamiento.fila not in filas_dict:
                filas_dict[aparcamiento.fila] = []
            filas_dict[aparcamiento.fila].append(aparcamiento)
        
        filas_ordenadas = sorted(filas_dict.keys())
        for fila in filas_ordenadas:
            filas_dict[fila].sort(key=lambda a: a.columna)
        
        # Calcular altura total necesaria
        num_filas = len(filas_ordenadas)
        altura_total = num_filas * (alto_plaza + espacio_y)
        
        # Empezar desde abajo del canvas
        canvas_height = 800
        y_inicial = canvas_height - 200  # Más espacio para evitar superposición con cabina
        
        # Dibujar de abajo hacia arriba (empezar más arriba para no superponer cabina)
        for idx, fila in enumerate(reversed(filas_ordenadas)):
            y_actual = y_inicial - ((idx + 1) * (alto_plaza + espacio_y))  # +1 para empezar una fila más arriba
            x_actual = margen_x
            
            for aparcamiento in filas_dict[fila]:
                # Determinar color
                if aparcamiento.ocupado:
                    color = 'red'
                elif aparcamiento.solo_minusvalidos:
                    color = 'lightblue'
                else:
                    color = 'lightgreen'
                
                # Dibujar rectángulo
                self.canvas.create_rectangle(
                    x_actual, y_actual, 
                    x_actual + ancho_plaza, y_actual + alto_plaza,
                    fill=color, outline='black', width=2
                )
                
                # ID del aparcamiento
                self.canvas.create_text(
                    x_actual + ancho_plaza/2, y_actual + 20,
                    text=aparcamiento.id, font=('Arial', 11, 'bold')
                )
                
                # Matrícula
                matricula_texto = aparcamiento.coche.matricula if aparcamiento.coche else "---"
                self.canvas.create_text(
                    x_actual + ancho_plaza/2, y_actual + 45,
                    text=matricula_texto, font=('Arial', 8)
                )
                
                # Indicador minusválido
                if aparcamiento.solo_minusvalidos:
                    self.canvas.create_text(
                        x_actual + ancho_plaza/2, y_actual + 60,
                        text="♿", font=('Arial', 10)
                    )
                
                x_actual += ancho_plaza + espacio_x
        
        # Dibujar cabina centrada debajo (en la posición original)
        total_ancho = self.parking.columnas * (ancho_plaza + espacio_x)
        cabina_ancho = 80
        cabina_alto = 50
        cabina_x = margen_x + (total_ancho / 2) - (cabina_ancho / 2)
        cabina_y = y_inicial + 20  # Posición original
        
        self.canvas.create_rectangle(
            cabina_x, cabina_y, 
            cabina_x + cabina_ancho, cabina_y + cabina_alto,
            fill='yellow', outline='black', width=3
        )
        self.canvas.create_text(
            cabina_x + cabina_ancho/2, cabina_y + cabina_alto/2, 
            text="CABINA", font=('Arial', 10, 'bold')
        )
    
    def entrada_vehiculo(self):
        """Procesa la entrada de un vehículo"""
        exito, mensaje = self.parking.cabina.procesar_entrada(self.parking)
        self.dibujar_parking()
    
    def salida_vehiculo(self):
        """Procesa la salida de un vehículo"""
        id_aparcamiento = simpledialog.askstring("Salida Vehículo", 
                                                 "Introduce el ID del aparcamiento (vacío para aleatorio):")
        if id_aparcamiento == "":
            id_aparcamiento = None
        elif id_aparcamiento:
            id_aparcamiento = id_aparcamiento.upper()
        else:
            return
        
        exito, mensaje = self.parking.cabina.procesar_salida(self.parking, id_aparcamiento)
        self.dibujar_parking()
    
    def toggle_automatico(self):
        """Activa/desactiva el modo automático"""
        self.automatico = not self.automatico
        if self.automatico:
            self.boton_automatico.config(text="Detener Automático", bg='darkred')
            logging.info("MODO AUTOMÁTICO ACTIVADO")
        else:
            self.boton_automatico.config(text="Iniciar Automático", bg='purple')
            logging.info("MODO AUTOMÁTICO DESACTIVADO")
    
    def proceso_automatico(self):
        """Proceso que simula entradas y salidas automáticas"""
        while True:
            if self.automatico:
                # Entrada aleatoria cada 3-8 segundos
                if random.random() < 0.5:
                    self.parking.cabina.procesar_entrada(self.parking)
                    self.ventana.after(0, self.dibujar_parking)
                
                # Salida aleatoria cada 5-12 segundos
                time.sleep(random.uniform(3, 8))
                if random.random() < 0.4 and self.automatico:
                    self.parking.cabina.procesar_salida(self.parking)
                    self.ventana.after(0, self.dibujar_parking)
            
            time.sleep(1)
    
    def guardar_estado(self):
        """Guarda el estado del parking"""
        self.parking.guardar_estado()
        messagebox.showinfo("Guardar", "Estado guardado correctamente")
    
    def iniciar(self):
        """Inicia la interfaz gráfica"""
        self.ventana.mainloop()

if __name__ == "__main__":
    logging.info("="*60)
    logging.info("INICIO DEL SISTEMA DE PARKING")
    logging.info("="*60)
    
    # Intentar cargar estado previo
    parking = Parking.cargar_estado()
    
    # Si no existe, crear uno nuevo
    if parking is None:
        print("Creando nuevo parking...")
        parking = Parking(filas=7, columnas=10, porcentaje_minusvalidos=0.15)
    
    interfaz = InterfazParking(parking)
    interfaz.iniciar()