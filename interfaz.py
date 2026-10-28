import math
import random
import tkinter as tk
from tkinter import filedialog, messagebox

from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.patches import Circle

# Constantes en el Sistema Internacional
G = 6.67430e-11  # m^3 / (kg * s^2)
M = 1.989e30  # kg (Masa del Sol)
R_SOL = 6.957e8  # m (radio del Sol, para detectar choques)
UA = 1.496e11  # m

# Velocidad de la animación, en días simulados por cuadro
VELOCIDAD_MIN = 0.1
VELOCIDAD_MAX = 30
VELOCIDAD_INICIAL = 1

# Zoom automático (la vista queda centrada en el Sol)
ZOOM_MARGEN = 1.3  # cuánto espacio dejar alrededor del planeta
ZOOM_VENTANA = 15  # cuadros recientes que se tienen en cuenta
ZOOM_SUAVIDAD = 0.2  # qué tan rápido se acerca al zoom buscado (0 a 1)
ZOOM_MINIMO = 0.03  # UA, para no acercarse infinitamente al Sol

# Explosión al chocar con el Sol
CUADROS_EXPLOSION = 75
N_LLAMAS = 170
N_CHISPAS = 80

# Color del fuego según el "calor" (1 = recién encendido, 0 = humo frío)
RAMPA_FUEGO = [
    (1.00, (1.00, 0.98, 0.90)),  # blanco
    (0.85, (1.00, 0.88, 0.30)),  # amarillo
    (0.65, (1.00, 0.60, 0.10)),  # naranja
    (0.45, (0.95, 0.30, 0.07)),  # naranja rojizo
    (0.28, (0.70, 0.12, 0.05)),  # rojo oscuro
    (0.12, (0.30, 0.20, 0.18)),  # humo
    (0.00, (0.16, 0.15, 0.15)),  # humo frío
]


def color_fuego(calor):
    """Interpola el color de la rampa de fuego para un calor entre 0 y 1."""
    calor = min(1.0, max(0.0, calor))
    for (c1, rgb1), (c2, rgb2) in zip(RAMPA_FUEGO, RAMPA_FUEGO[1:]):
        if calor >= c2:
            f = (calor - c2) / (c1 - c2)
            return tuple(b + f * (a - b) for a, b in zip(rgb1, rgb2))
    return RAMPA_FUEGO[-1][1]


def simular(x, y, vx, vy, dt, t_final):
    """Método de Euler, igual que en TP1V1.py. Recibe y devuelve unidades SI."""
    t = 0.0
    tabla_datos = [[t, x, y, vx, vy]]
    choco = False

    while t < t_final:
        r = math.sqrt(x**2 + y**2)

        # Aceleración en m/s^2
        ax = -G * M * x / (r**3)
        ay = -G * M * y / (r**3)

        # Actualización según método de Euler
        x_ant, y_ant = x, y
        x = x + vx * dt
        y = y + vy * dt
        vx = vx + ax * dt
        vy = vy + ay * dt
        t = t + dt

        # Choque: se mira el segmento recorrido en este paso, no sólo el punto
        # final, porque cerca del Sol un paso puede "saltar" por encima de él
        dx, dy = x - x_ant, y - y_ant
        largo2 = dx**2 + dy**2
        s = -(x_ant * dx + y_ant * dy) / largo2 if largo2 > 0 else 1.0
        s = min(1.0, max(0.0, s))
        xc, yc = x_ant + s * dx, y_ant + s * dy  # punto del segmento más cercano al Sol
        if math.sqrt(xc**2 + yc**2) < R_SOL:
            tabla_datos.append([t, xc, yc, vx, vy])
            choco = True
            break

        tabla_datos.append([t, x, y, vx, vy])

    return tabla_datos, choco


def armar_animacion(fig, tabla_datos, choco=False, velocidad=lambda: VELOCIDAD_INICIAL,
                    zoom_automatico=lambda: True):
    """Dibuja la animación de la órbita sobre la figura dada y la devuelve.

    velocidad es una función que devuelve cuántos días simulados avanza cada
    cuadro, y zoom_automatico una que dice si la escala se ajusta sola. Las dos
    se consultan en cada cuadro, así se pueden cambiar mientras corre.
    """
    xs = [fila[1] / UA for fila in tabla_datos]
    ys = [fila[2] / UA for fila in tabla_datos]
    n = len(tabla_datos)
    dt = tabla_datos[1][0] - tabla_datos[0][0] if n > 1 else 86400

    def pasos_por_cuadro():
        return velocidad() * 86400 / dt

    def generar_cuadros():
        i = 0.0
        while int(i) < n - 1:
            yield int(i)
            i += pasos_por_cuadro()
        yield n - 1
        # Si chocó, se agregan cuadros extra para la explosión
        if choco:
            yield from range(n, n + CUADROS_EXPLOSION)

    # Cantidad de cuadros con la velocidad actual (matplotlib la necesita para guardar el GIF)
    total_cuadros = math.ceil((n - 1) / pasos_por_cuadro()) + 1
    if choco:
        total_cuadros += CUADROS_EXPLOSION

    fig.clear()
    fig.patch.set_facecolor("black")
    ax = fig.add_subplot(111)
    ax.set_facecolor("black")

    # Escala fija: entra la trayectoria completa
    limite_fijo = 1.25 * max(max(abs(v) for v in xs), max(abs(v) for v in ys))
    # Escala automática: se ajusta cuadro a cuadro según la distancia al Sol
    radios = [math.sqrt(x**2 + y**2) for x, y in zip(xs, ys)]
    zoom = {"actual": max(ZOOM_MARGEN * radios[0], ZOOM_MINIMO), "recientes": []}

    def ajustar_zoom(i):
        if not zoom_automatico():
            limite = limite_fijo
        else:
            zoom["recientes"] = (zoom["recientes"] + [radios[i]])[-ZOOM_VENTANA:]
            buscado = max(ZOOM_MARGEN * max(zoom["recientes"]), ZOOM_MINIMO)
            limite = zoom["actual"] + ZOOM_SUAVIDAD * (buscado - zoom["actual"])
            limite = max(limite, 1.08 * radios[i])  # que el planeta nunca quede afuera
        zoom["actual"] = limite
        ax.set_xlim(-limite, limite)
        ax.set_ylim(-limite, limite)

    ax.set_xlim(-zoom["actual"], zoom["actual"])
    ax.set_ylim(-zoom["actual"], zoom["actual"])
    ax.set_aspect("equal")
    ax.set_xlabel("x [UA]", color="#888888")
    ax.set_ylabel("y [UA]", color="#888888")
    ax.tick_params(colors="#666666")
    for borde in ax.spines.values():
        borde.set_color("#333333")
    ax.set_title("Órbita del planeta alrededor del Sol", color="white", pad=12)

    # Sol con un halo
    for tam, alfa in [(2500, 0.05), (1200, 0.10), (600, 0.20)]:
        ax.scatter([0], [0], s=tam, color="#ffaa00", alpha=alfa, linewidths=0, zorder=2)
    ax.scatter([0], [0], s=250, color="#ffd23f", zorder=3)
    # Sol en tamaño real: sólo se nota cuando el zoom se acerca mucho
    ax.add_patch(Circle((0, 0), R_SOL / UA, color="#ffd23f", zorder=3))

    # Trayectoria recorrida, estela brillante y el planeta
    trayectoria, = ax.plot([], [], color="#2f6fd6", linewidth=1.0, alpha=0.6, zorder=4)
    estela, = ax.plot([], [], color="#6ec6ff", linewidth=2.5, zorder=5)
    planeta, = ax.plot([], [], "o", color="#4fc3f7", markersize=9,
                       markeredgecolor="white", markeredgewidth=0.8, zorder=6)
    texto = ax.text(0.03, 0.97, "", transform=ax.transAxes, color="white",
                    fontsize=11, va="top", family="monospace")

    # Elementos de la explosión (vacíos hasta que ocurra el choque)
    onda = ax.scatter([], [], s=0, facecolors="none", edgecolors="#ffb347",
                      linewidths=2, zorder=7)
    llamas = ax.scatter([], [], s=0, linewidths=0, zorder=8)
    bola = [ax.scatter([], [], s=0, linewidths=0, zorder=9 + j) for j in range(3)]
    chispas = ax.scatter([], [], s=0, linewidths=0, zorder=12)
    cartel = ax.text(0.5, 0.12, "¡CHOQUE!", transform=ax.transAxes, color="#ff6a1f",
                     fontsize=22, fontweight="bold", ha="center", alpha=0, zorder=13)
    explosion = [onda, llamas, *bola, chispas, cartel]

    azar = random.Random(0)
    # Las distancias de llamas y chispas son proporciones de la escala visible
    # Llamas: salen despacio, se agrandan, se enfrían y terminan en humo
    llamas_datos = []
    for _ in range(N_LLAMAS):
        angulo = azar.uniform(0, 2 * math.pi)
        rapidez = azar.uniform(0.02, 0.32)
        llamas_datos.append({
            "dx": rapidez * math.cos(angulo),
            "dy": rapidez * math.sin(angulo),
            "tam": azar.uniform(80, 420),
            "enfriamiento": azar.uniform(0.9, 2.0),
            "subida": azar.uniform(0.02, 0.10),
        })
    # Chispas: salen rápido, son chicas y se apagan pronto
    chispas_datos = []
    for _ in range(N_CHISPAS):
        angulo = azar.uniform(0, 2 * math.pi)
        rapidez = azar.uniform(0.25, 0.75)
        chispas_datos.append({
            "dx": rapidez * math.cos(angulo),
            "dy": rapidez * math.sin(angulo),
            "tam": azar.uniform(3, 14),
            "vida": azar.uniform(0.25, 0.7),
        })

    def explotar(k):
        avance = k / (CUADROS_EXPLOSION - 1)  # de 0 a 1
        salida = 1 - (1 - avance) ** 3  # rápido al principio, después frena
        x0, y0 = xs[-1], ys[-1]
        escala = zoom["actual"]  # durante la explosión la escala queda quieta
        planeta.set_data([], [])
        estela.set_data([], [])

        # Resplandor del fondo en los primeros cuadros
        brillo = max(0.0, 1 - 4 * avance)
        ax.set_facecolor((0.30 * brillo, 0.10 * brillo, 0.02 * brillo))

        # Onda expansiva
        onda.set_offsets([(x0, y0)])
        onda.set_sizes([60000 * salida])
        onda.set_alpha(max(0.0, 0.8 * (1 - 2.5 * avance)))

        # Bola de fuego: tres capas (exterior roja, media naranja, núcleo blanco)
        for j, capa in enumerate(bola):
            calor = 1.0 - 0.15 * (2 - j) - 0.9 * avance
            parpadeo = azar.uniform(0.85, 1.15)
            crecimiento = math.sin(min(1.0, 2.2 * avance) * math.pi / 2)
            capa.set_offsets([(x0, y0)])
            capa.set_sizes([(3500 - 1100 * j) * (0.3 + crecimiento) * parpadeo])
            opacidad = (0.35 + 0.25 * j) * max(0.0, 1 - 1.4 * avance)
            capa.set_facecolor([(*color_fuego(calor), opacidad)])

        # Llamas que se convierten en humo
        posiciones, tamanos, colores = [], [], []
        for d in llamas_datos:
            calor = 1 - d["enfriamiento"] * avance
            posiciones.append((x0 + escala * d["dx"] * salida,
                               y0 + escala * (d["dy"] * salida + d["subida"] * avance**2)))
            tamanos.append(d["tam"] * (0.4 + 2.2 * salida) * azar.uniform(0.9, 1.1))
            alfa = (0.75 if calor > 0.15 else 0.45) * (1 - avance**2)
            colores.append((*color_fuego(calor), alfa))
        llamas.set_offsets(posiciones)
        llamas.set_sizes(tamanos)
        llamas.set_facecolor(colores)

        # Chispas que caen un poco y se apagan
        posiciones, tamanos, colores = [], [], []
        for d in chispas_datos:
            vida = min(1.0, avance / d["vida"])
            posiciones.append((x0 + escala * d["dx"] * salida,
                               y0 + escala * (d["dy"] * salida - 0.08 * avance**2)))
            tamanos.append(d["tam"] * (1 - 0.6 * vida))
            colores.append((*color_fuego(1 - 0.6 * vida), 1 - vida))
        chispas.set_offsets(posiciones)
        chispas.set_sizes(tamanos)
        chispas.set_facecolor(colores)

        cartel.set_alpha(min(1.0, 2 * avance))
        cartel.set_color(color_fuego(0.75 + 0.15 * math.sin(k * 0.8)))
        return trayectoria, estela, planeta, texto, *explosion

    def actualizar(i):
        if i >= n:
            return explotar(i - n)
        ajustar_zoom(i)
        trayectoria.set_data(xs[:i + 1], ys[:i + 1])
        # Estela: los últimos 15 días (o 3 cuadros, si la animación va muy rápida)
        largo_estela = max(15 * 86400 / dt, 3 * pasos_por_cuadro())
        inicio_estela = max(0, i - int(largo_estela))
        estela.set_data(xs[inicio_estela:i + 1], ys[inicio_estela:i + 1])
        planeta.set_data([xs[i]], [ys[i]])
        t_dias = tabla_datos[i][0] / 86400
        vx_i, vy_i = tabla_datos[i][3], tabla_datos[i][4]
        v = math.sqrt(vx_i**2 + vy_i**2) / 1000
        r = math.sqrt(xs[i]**2 + ys[i]**2)
        texto.set_text(f"t = {t_dias:7.1f} días\nr = {r:.4f} UA\nv = {v:.2f} km/s")
        return trayectoria, estela, planeta, texto, *explosion

    return FuncAnimation(fig, actualizar, frames=generar_cuadros, interval=20,
                         save_count=total_cuadros, cache_frame_data=False,
                         blit=False, repeat=False)


class Interfaz:
    def __init__(self, raiz):
        self.raiz = raiz
        self.anim = None
        self.tabla_datos = None
        self.choco = False
        raiz.title("TP1 - Órbita de un planeta")
        raiz.configure(bg="black")

        panel = tk.Frame(raiz, bg="#111111", padx=14, pady=14)
        panel.pack(side=tk.LEFT, fill=tk.Y)

        tk.Label(panel, text="Condiciones iniciales", bg="#111111", fg="white",
                 font=("TkDefaultFont", 12, "bold")).pack(anchor="w", pady=(0, 10))

        # (etiqueta, valor por defecto) — por defecto, la Tierra
        campos = [
            ("x₀ [UA]", "1.0"),
            ("y₀ [UA]", "0.0"),
            ("vx₀ [km/s]", "0.0"),
            ("vy₀ [km/s]", "29.78"),
            ("Δt [horas]", "1"),
            ("Tiempo final [días]", "365"),
        ]
        self.entradas = []
        for etiqueta, defecto in campos:
            tk.Label(panel, text=etiqueta, bg="#111111", fg="#bbbbbb").pack(anchor="w")
            entrada = tk.Entry(panel, width=14, bg="#222222", fg="white",
                               insertbackground="white", relief=tk.FLAT)
            entrada.insert(0, defecto)
            entrada.pack(anchor="w", pady=(0, 8), ipady=3)
            self.entradas.append(entrada)

        tk.Button(panel, text="Simular", command=self.simular,
                  bg="#2f6fd6", fg="white", activebackground="#4a86e8",
                  relief=tk.FLAT, padx=10, pady=4).pack(fill=tk.X, pady=(8, 4))
        tk.Button(panel, text="Guardar GIF", command=self.guardar_gif,
                  bg="#333333", fg="white", activebackground="#444444",
                  relief=tk.FLAT, padx=10, pady=4).pack(fill=tk.X)

        # Se puede mover mientras corre la animación
        tk.Label(panel, text="Velocidad [días/cuadro]", bg="#111111",
                 fg="#bbbbbb").pack(anchor="w", pady=(14, 0))
        self.velocidad = tk.Scale(panel, from_=VELOCIDAD_MIN, to=VELOCIDAD_MAX,
                                  resolution=0.1, orient=tk.HORIZONTAL, length=160,
                                  bg="#111111", fg="white", troughcolor="#222222",
                                  activebackground="#4a86e8", highlightthickness=0,
                                  relief=tk.FLAT)
        self.velocidad.set(VELOCIDAD_INICIAL)
        self.velocidad.pack(anchor="w")

        self.zoom_auto = tk.BooleanVar(value=True)
        tk.Checkbutton(panel, text="Zoom automático", variable=self.zoom_auto,
                       bg="#111111", fg="#bbbbbb", selectcolor="#222222",
                       activebackground="#111111", activeforeground="white",
                       highlightthickness=0).pack(anchor="w", pady=(8, 0))

        self.estado = tk.Label(panel, text="", bg="#111111", fg="#888888",
                               wraplength=160, justify=tk.LEFT)
        self.estado.pack(anchor="w", pady=(12, 0))

        self.fig = Figure(figsize=(7, 7), facecolor="black")
        self.lienzo = FigureCanvasTkAgg(self.fig, master=raiz)
        self.lienzo.get_tk_widget().pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.simular()

    def leer_datos(self):
        try:
            x0, y0, vx0, vy0, dt_h, t_dias = [float(e.get().replace(",", "."))
                                              for e in self.entradas]
        except ValueError:
            messagebox.showerror("Error", "Todos los campos tienen que ser números.")
            return None
        if dt_h <= 0 or t_dias <= 0:
            messagebox.showerror("Error", "Δt y el tiempo final tienen que ser positivos.")
            return None
        if x0 == 0 and y0 == 0:
            messagebox.showerror("Error", "El planeta no puede empezar en el Sol.")
            return None
        # Paso todo a unidades SI
        return x0 * UA, y0 * UA, vx0 * 1000, vy0 * 1000, dt_h * 3600, t_dias * 86400

    def simular(self):
        datos = self.leer_datos()
        if datos is None:
            return
        # Si la animación anterior ya terminó, matplotlib deja event_source en None
        if self.anim is not None and self.anim.event_source is not None:
            self.anim.event_source.stop()

        self.tabla_datos, self.choco = simular(*datos)
        texto = f"Puntos calculados: {len(self.tabla_datos)}"
        if self.choco:
            texto += "\nEl planeta chocó contra el Sol."
        self.estado.config(text=texto)

        self.anim = armar_animacion(self.fig, self.tabla_datos, self.choco,
                                    self.velocidad.get, self.zoom_auto.get)
        self.lienzo.draw()

    def guardar_gif(self):
        if self.tabla_datos is None:
            return
        ruta = filedialog.asksaveasfilename(defaultextension=".gif",
                                            initialfile="orbita.gif",
                                            filetypes=[("GIF", "*.gif")])
        if not ruta:
            return
        self.estado.config(text="Guardando GIF...")
        self.raiz.update()
        # Figura aparte, para no interferir con la animación de la ventana
        fig_gif = Figure(figsize=(7, 7), facecolor="black")
        # El GIF usa la velocidad que tenga el deslizador al apretar el botón
        velocidad_gif = self.velocidad.get()
        zoom_gif = self.zoom_auto.get()
        armar_animacion(fig_gif, self.tabla_datos, self.choco,
                        lambda: velocidad_gif, lambda: zoom_gif).save(ruta, writer=PillowWriter(fps=30))
        self.estado.config(text=f"GIF guardado en:\n{ruta}")


if __name__ == "__main__":
    raiz = tk.Tk()
    Interfaz(raiz)
    raiz.mainloop()
