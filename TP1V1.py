import math
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter

# Constantes en el Sistema Internacional
G = 6.67430e-11  # m^3 / (kg * s^2)
M = 1.989e30  # kg (Masa del Sol)

# Paso de tiempo: 1 hora (3600 segundos)
dt = 3600.0
# Simular 1 año completo en segundos
t_final = 365 * 24 * 3600.0

# Condiciones iniciales (Tierra a ~1 AU del Sol)
t = 0.0
x = 1.496e11  # m
y = 0.0  # m
vx = 0.0  # m/s
vy = 29780.0  # m/s (velocidad orbital real de la Tierra)

tabla_datos = []
tabla_datos.append([t, x, y, vx, vy])

while t < t_final:
    r = math.sqrt(x**2 + y**2)

    # Aceleración en m/s^2 con constantes reales
    ax = -G * M * x / (r**3)
    ay = -G * M * y / (r**3)

    # Actualización según método de Euler
    x = x + vx * dt
    y = y + vy * dt
    vx = vx + ax * dt
    vy = vy + ay * dt
    t = t + dt

    tabla_datos.append([t, x, y, vx, vy])

print(f"Puntos calculados: {len(tabla_datos)}")
print(f"Posición final (x, y) en metros: ({x:.3e}, {y:.3e})")

# Animación de la trayectoria (en unidades astronómicas para que se lea mejor)
UA = 1.496e11  # m
xs = [fila[1] / UA for fila in tabla_datos]
ys = [fila[2] / UA for fila in tabla_datos]

# Un cuadro de animación por día (dt = 1 h => 24 pasos por cuadro)
pasos_por_cuadro = int(24 * 3600 / dt)
cuadros = range(0, len(tabla_datos), pasos_por_cuadro)

plt.style.use("dark_background")
fig, ax = plt.subplots(figsize=(7, 7))
fig.patch.set_facecolor("black")
ax.set_facecolor("black")

limite = 1.25 * max(max(abs(v) for v in xs), max(abs(v) for v in ys))
ax.set_xlim(-limite, limite)
ax.set_ylim(-limite, limite)
ax.set_aspect("equal")
ax.set_xlabel("x [UA]", color="#888888")
ax.set_ylabel("y [UA]", color="#888888")
ax.tick_params(colors="#666666")
for borde in ax.spines.values():
    borde.set_color("#333333")
ax.set_title("Órbita de la Tierra alrededor del Sol", color="white", pad=12)

# Sol con un halo
for tam, alfa in [(2500, 0.05), (1200, 0.10), (600, 0.20)]:
    ax.scatter([0], [0], s=tam, color="#ffaa00", alpha=alfa, linewidths=0, zorder=2)
ax.scatter([0], [0], s=250, color="#ffd23f", zorder=3)

# Trayectoria recorrida, estela brillante y la Tierra
trayectoria, = ax.plot([], [], color="#2f6fd6", linewidth=1.0, alpha=0.6, zorder=4)
estela, = ax.plot([], [], color="#6ec6ff", linewidth=2.5, zorder=5)
tierra, = ax.plot([], [], "o", color="#4fc3f7", markersize=9,
                  markeredgecolor="white", markeredgewidth=0.8, zorder=6)
texto = ax.text(0.03, 0.97, "", transform=ax.transAxes, color="white",
                fontsize=11, va="top", family="monospace")


def actualizar(i):
    trayectoria.set_data(xs[:i + 1], ys[:i + 1])
    inicio_estela = max(0, i - 15 * pasos_por_cuadro)  # últimos 15 días
    estela.set_data(xs[inicio_estela:i + 1], ys[inicio_estela:i + 1])
    tierra.set_data([xs[i]], [ys[i]])
    t_dias = tabla_datos[i][0] / 86400
    vx_i, vy_i = tabla_datos[i][3], tabla_datos[i][4]
    v = math.sqrt(vx_i**2 + vy_i**2) / 1000
    r = math.sqrt(xs[i]**2 + ys[i]**2)
    texto.set_text(f"t = {t_dias:6.1f} días\nr = {r:.4f} UA\nv = {v:.2f} km/s")
    return trayectoria, estela, tierra, texto


anim = FuncAnimation(fig, actualizar, frames=cuadros, interval=20, blit=True,
                     repeat=False)

guardar_gif = True
if guardar_gif:
    anim.save("orbita_tierra.gif", writer=PillowWriter(fps=30))

plt.show()
