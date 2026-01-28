# CAMBIOS.md

## 1. Interfaz Pública Definida

### Métodos implementados en la clase `Parking`:

#### `entrar(matricula=None, es_minusvalido=False, es_electrico=False)`

**Por qué:** Centraliza toda la lógica de entrada de vehículos. Permite tanto entrada automática (sin parámetros) como manual (con matrícula y características específicas). Devuelve información estructurada sobre el éxito de la operación.

**Retorna:** `(éxito: bool, mensaje: str, plaza_id: str|None)`

#### `salir(matricula)`

**Por qué:** Punto único de salida de vehículos usando la matrícula como identificador. Encapsula el cálculo de tarifas y la liberación de la plaza. La GUI no necesita saber cómo se busca el vehículo ni cómo se calcula el precio.

**Retorna:** `(éxito: bool, mensaje: str, tarifa: float)`

#### `listar_coches()`

**Por qué:** Proporciona información completa de todos los vehículos estacionados sin exponer la estructura interna de aparcamientos. La GUI solo recibe los datos que necesita mostrar.

**Retorna:** `list[dict]` con matrícula, plaza, tipo, características y tiempo

#### `plazas_libres(tipo=None)`

**Por qué:** Permite consultar disponibilidad general o por tipo específico de plaza. Útil para validaciones previas y estadísticas sin necesidad de iterar sobre la estructura interna.

**Retorna:** `int` (número de plazas disponibles)

#### `resumen()`

**Por qué:** Proporciona una vista completa del estado del parking con estadísticas agregadas. Evita que la GUI tenga que calcular porcentajes u ocupación recorriendo todas las plazas.

**Retorna:** `dict` con totales, ocupación, desglose por tipo y tarifa activa

#### `cambiar_tarifa(estrategia)`

**Por qué:** Permite modificar el comportamiento de tarificación en tiempo de ejecución sin reiniciar el sistema. Implementa el principio de inversión de dependencias.

**Retorna:** `None` (modifica estado interno)

---

## 2. Decisión Centralizada

### Regla: **Compatibilidad entre vehículo y tipo de plaza**

**Dónde:** Método `puede_ocupar()` en la clase `Aparcamiento`

```python
def puede_ocupar(self, coche):
    if self.ocupado:
        return False

    # Plaza de minusválidos solo para coches con tarjeta
    if self.tipo == TipoPlaza.MINUSVALIDO and not coche.es_minusvalido:
        return False

    # Plaza eléctrica solo para coches eléctricos
    if self.tipo == TipoPlaza.ELECTRICO and not coche.es_electrico:
        return False

    return True
```

**Justificación:**

- Esta regla está en el propio objeto `Aparcamiento` porque cada plaza "conoce" sus propias restricciones
- Evita duplicar esta lógica en múltiples lugares (entrada manual, entrada automática, etc.)
- Si en el futuro se añaden nuevos tipos de plaza, solo hay que modificar este método
- Sigue el principio de responsabilidad única: el aparcamiento decide si puede ser ocupado
- Facilita el testing: se puede probar esta regla de forma aislada

**Alternativas descartadas:**

- Poner la lógica en `Parking.entrar()`: dispersaría la responsabilidad
- Poner la lógica en `Coche`: un coche no debería saber qué plazas existen
- Poner la lógica en `Cabina`: no es responsabilidad de la cabina conocer tipos de plaza

---

## 3. Cambios Futuros Preparados

### 3.1 Sistema de Tarifas (Patrón Strategy) Implementado

**Qué permite:**

- Añadir nuevas estrategias de tarificación sin modificar código existente
- Cambiar la tarifa en tiempo real durante la operación del parking
- Testar cada estrategia de forma independiente

**Estrategias implementadas:**

1. **TarifaEstandar**: Tarifa fija (1.5€/20s después de 30s gratis)
2. **TarifaPorTramos**: Tarifa variable según hora del día (punta/valle)
3. **TarifaDiferenciada**: Descuentos/recargos según tipo de vehículo

**Cómo extender:**

```python
class TarifaPorDia(EstrategiaTarifa):
    def calcular(self, tiempo, coche, tipo_plaza):
        # Fin de semana más barato
        if datetime.now().weekday() >= 5:
            return tiempo.total_seconds() * 0.03
        return tiempo.total_seconds() * 0.05

    def get_nombre(self):
        return "Por Día Semana"
```

### 3.2 Tipos de Plaza Extensibles Implementado

**Qué permite:**

- Añadir nuevos tipos de plaza (motos, furgonetas, carga rápida, etc.)
- Cada tipo puede tener sus propias restricciones
- Configuración flexible al crear el parking

**Tipos implementados:**

- `TipoPlaza.NORMAL`
- `TipoPlaza.MINUSVALIDO`
- `TipoPlaza.ELECTRICO`

**Cómo extender:**

```python
class TipoPlaza:
    NORMAL = "normal"
    MINUSVALIDO = "minusvalido"
    ELECTRICO = "electrico"
    MOTO = "moto"              # Nuevo
    FURGONETA = "furgoneta"    # Nuevo
```

### 3.3 Sistema de Reservas (Preparado, no implementado)

**Cómo implementar:**

1. Añadir atributos a `Aparcamiento`:

   ```python
   self.reservado = False
   self.reserva_hasta = None
   self.reservado_por = None
   ```

2. Nuevo método en `Parking`:

   ```python
   def reservar(self, plaza_id, matricula, duracion_minutos):
       # Lógica de reserva
   ```

3. Modificar `puede_ocupar()` para verificar reservas

4. Añadir método de limpieza de reservas expiradas

### 3.4 Tipos de Parking (Preparado con herencia)

**Cómo implementar:**

```python
class ParkingCubierto(Parking):
    def __init__(self, filas, columnas):
        super().__init__(filas, columnas)
        self.tiene_techo = True
        self.iluminacion_24h = True

class ParkingMultinivel(Parking):
    def __init__(self, filas, columnas, niveles):
        self.niveles = niveles
        # Crear parking por nivel
```

---

## 4. Qué Parte Me Ayudó Más a Entender la POO

### **El Patrón Strategy para las Tarifas**

**Antes de implementarlo:**

- Pensaba que cambiar el comportamiento requería modificar la clase principal
- No veía claro cómo separar "lo que se hace" de "cómo se hace"
- Tendía a usar muchos `if-elif` para diferentes casos

**Después de implementarlo:**

- **Comprendo la abstracción**: Una interfaz (clase abstracta) define QUÉ se debe hacer, las implementaciones definen CÓMO
- **Polimorfismo en acción**: El `Parking` no necesita saber qué estrategia está usando, solo llama a `calcular()`
- **Principio Open/Closed**: Abierto a extensión (nuevas tarifas) pero cerrado a modificación (no tocar `Parking`)
- **Responsabilidad única**: Cada clase de tarifa tiene UNA razón para cambiar

**Ejemplo concreto:**

```python
# La cabina no sabe qué estrategia usa
def calcular_tarifa(self, tiempo, coche, tipo_plaza):
    return self.estrategia_tarifa.calcular(tiempo, coche, tipo_plaza)

# Pero puede cambiarla fácilmente
parking.cambiar_tarifa(TarifaPorTramos())
```

Esto me hizo ver que **POO no es solo agrupar datos y funciones**, sino:

- Diseñar para el cambio
- Minimizar dependencias
- Delegar responsabilidades adecuadamente
- Pensar en contratos (interfaces) más que en implementaciones

### **Encapsulación con la Interfaz Pública**

**Antes:**

```python
# La GUI accedía directamente
for aparcamiento in parking.aparcamientos:
    if aparcamiento.ocupado:
        # ...
```

**Después:**

```python
# La GUI usa la interfaz
coches = parking.listar_coches()
for coche in coches:
    # ...
```

**Aprendizaje:**

- Las estructuras internas pueden cambiar sin romper la GUI
- Podría cambiar `aparcamientos` de lista a diccionario y la GUI seguiría funcionando
- Los métodos públicos actúan como "contrato" entre módulos

---

## 5. Cómo Usé la IA

### **Lo que acepté:**

1. **Estructura del Patrón Strategy**
   - La IA sugirió usar clases abstractas con `ABC` y `@abstractmethod`
   - Propuso la separación en `EstrategiaTarifa` base y estrategias concretas
   - **Por qué lo acepté:** Es el patrón estándar en Python, bien documentado y extensible

2. **Separación de responsabilidades**
   - Mover lógica de búsqueda de plazas de `Cabina` a `Parking`
   - `Cabina` solo genera vehículos y calcula tarifas
   - **Por qué lo acepté:** Tiene sentido semántico, la cabina no debería "buscar" dentro del parking

3. **Método `puede_ocupar()` en Aparcamiento**
   - Centralizar la lógica de compatibilidad en la propia plaza
   - **Por qué lo acepté:** Cada objeto debe conocer sus propias reglas (encapsulación)

4. **Diseño de la interfaz pública con tuplas de retorno**
   - Retornar `(éxito, mensaje, dato)` en lugar de lanzar excepciones
   - **Por qué lo acepté:** Más pythónico para este caso de uso, fácil de desempaquetar

### **Lo que descarté o modifiqué:**

1. **Sistema de eventos/observadores**
   - La IA sugirió un patrón Observer para notificar cambios a la GUI
   - **Por qué lo descarté:** Demasiado complejo para este proyecto, `self.actualizar_vista()` es suficiente

2. **Base de datos en lugar de JSON**
   - Propuesta de usar SQLite para persistencia
   - **Por qué lo descarté:** Los requisitos especifican mantener JSON, y es más simple para este caso

3. **Validación exhaustiva de matrículas**
   - Regex complejo para validar formato de matrículas españolas
   - **Por qué lo modifiqué:** Simplifiqué a `.upper().strip()`, suficiente para un simulador

4. **Tipos de datos complejos (dataclasses, TypedDict)**
   - Sugerencia de usar `@dataclass` para `Coche` y `Aparcamiento`
   - **Por qué lo descarté parcialmente:** Mantuve clases simples por compatibilidad con JSON, pero reconozco que sería mejor práctica

5. **Logging extensivo**
   - Propuesta de mantener logs estructurados con niveles
   - **Por qué lo descarté:** Requisito explícito de eliminar el sistema de logging

### **Lo que adapté:**

1. **Sistema de colores en la interfaz**
   - La IA propuso paleta específica
   - **Lo adapté:** Ajusté colores para mejor contraste y accesibilidad

2. **Organización del canvas**
   - Sugerencia inicial dibujaba de arriba hacia abajo
   - **Lo adapté:** Mantuve el diseño original de abajo hacia arriba, más intuitivo para un parking

3. **Método `resumen()`**
   - IA propuso solo porcentaje de ocupación
   - **Lo expandí:** Añadí desglose por tipo de plaza, más útil para el usuario

---

## Conclusión

Este proyecto me ayudó a entender que POO no es solo sintaxis (clases, herencia, etc.) sino **diseño y arquitectura**. Las decisiones importantes son:

- Dónde poner cada responsabilidad
- Cómo preparar el código para cambios futuros
- Qué exponer y qué ocultar
