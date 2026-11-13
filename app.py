"""
Evaluación Diagnóstica · Preparación y Respuesta a Emergencias
Maestría en Prevención de Riesgos Laborales · Sesión 1
10 preguntas (M1: 3 · M2: 4 · M3: 3) · 10 pts c/u · 3 niveles: Básico / Intermedio / Avanzado
Caso ficticio: Industrias Alimentarias Pachakuti S.A.C. (Arequipa)
La ED es diagnóstica (sin calificación en el sílabo): el puntaje sirve para ubicar saberes previos.
"""
import os
import json
import time
import random
import sqlite3
from contextlib import closing
from datetime import datetime

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Evaluación Diagnóstica · Emergencias", page_icon="🧭", layout="centered")

DB = os.environ.get("ED_DB", "diagnostica.db")
NAVY, PANEL, TEAL, GOLD, TXT = "#050D1A", "#0E1F3A", "#14B8A6", "#F2B01E", "#F5F8FC"

# ── Umbrales (criterio docente propuesto; ajústalos aquí) ──────────────────────
PUNTOS_POR_PREGUNTA = 10
UMBRAL_AVANZADO = 80      # 80-100
UMBRAL_INTERMEDIO = 50    # 50-70   (Básico: 0-40)

MODULOS = {1: "Módulo 1 · Administración, liderazgo y marco legal",
           2: "Módulo 2 · Planes, protección, brigadas y continuidad",
           3: "Módulo 3 · Simulacros, comando y mejora"}
SESIONES = {1: "sesiones 1 y 2", 2: "sesiones 3 y 4", 3: "sesiones 5 y 6"}

st.markdown(f"""
<style>
.stApp {{ background:{NAVY}; }}
.stApp p, .stApp li, .stApp label, .stApp [data-testid="stMarkdownContainer"] {{ color:{TXT}; }}
[data-testid="stSidebar"] {{ background:{PANEL}; }}
[data-testid="stSidebar"] * {{ color:{TXT}; }}
h1,h2,h3,h4 {{ color:{GOLD} !important; }}
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {{ color:#CBD5E1 !important; }}
[data-testid="stWidgetLabel"] p, label p {{ color:{TXT} !important; font-weight:600; }}
div[role="radiogroup"] label {{ background:{PANEL}; border:1px solid #27466F; border-radius:8px;
    padding:8px 12px; margin-bottom:6px; }}
div[role="radiogroup"] label:hover {{ border-color:{TEAL}; }}
div[role="radiogroup"] label p {{ color:{TXT} !important; font-weight:500; }}
input, textarea {{ color:{TXT} !important; background:{PANEL} !important; }}
[data-testid="stExpander"] {{ background:{PANEL}; border:1px solid #27466F; border-radius:8px; }}
[data-testid="stExpander"] summary p {{ color:{TXT} !important; font-weight:600; }}
[data-testid="stMetricLabel"] p, [data-testid="stMetricValue"] {{ color:{TXT} !important; }}
.stButton>button, .stDownloadButton>button {{ border:1px solid {TEAL}; color:{TXT}; background:{PANEL}; }}
.stButton>button[kind="primary"] {{ background:{TEAL}; color:#04121F !important; font-weight:800; border:none; }}
.card {{ background:{PANEL}; border-left:5px solid {TEAL}; padding:14px 18px; border-radius:8px; margin-bottom:12px; color:{TXT}; }}
.gold {{ color:{GOLD}; font-weight:700; }}
.badge {{ display:inline-block; background:{GOLD}; color:#04121F !important; padding:4px 12px;
         border-radius:14px; margin:3px; font-weight:700; }}
.ficticio {{ background:#3b2f0a; border:1px solid {GOLD}; padding:8px 12px; border-radius:6px;
            font-size:.85rem; color:#FFE9A8 !important; }}
.ficticio b {{ color:#FFE9A8 !important; }}
.nivel {{ font-size:1.6rem; font-weight:800; color:#04121F !important; background:{GOLD};
         padding:8px 22px; border-radius:30px; display:inline-block; }}
.score {{ font-size:3.2rem; font-weight:800; color:{TEAL} !important; line-height:1; }}
</style>
""", unsafe_allow_html=True)

# ── Preguntas ──────────────────────────────────────────────────────────────────
QS = [
    dict(id=1, mod=1, tema="Glosario operativo",
         q="En Pachakuti, un cortocircuito genera humo en un tablero y la brigada lo controla con extintores en 5 minutos "
           "sin afectar la producción. Días después, un incendio mayor paraliza la planta, hay lesionados y un video se "
           "difunde en redes. ¿Qué afirmación distingue correctamente ambos eventos?",
         ok="El primero es una emergencia manejable con los procedimientos y recursos previstos; el segundo puede escalar a crisis "
            "porque amenaza personas, operación y reputación y exige decisiones de la dirección.",
         mal=["Ambos son crisis porque hubo fuego.",
              "El primero es un desastre y el segundo una contingencia.",
              "No hay diferencia: son sinónimos en la gestión de emergencias."],
         fb="Una emergencia se maneja con procedimientos y recursos previstos; una crisis compromete la viabilidad, la reputación o "
            "los objetivos de la organización y exige decisiones de la dirección bajo incertidumbre. Un evento puede escalar de "
            "emergencia a crisis. (Definición operativa de trabajo; en clase la contrastaremos con el glosario normativo)."),
    dict(id=2, mod=1, tema="Marco legal y rol de la Alta Gerencia",
         q="Ocurre un accidente grave y se comprueba que la empresa no tenía plan de preparación y respuesta ante emergencias. "
           "Según el principio de responsabilidad de la Ley 29783, ¿quién asume en primer término las consecuencias "
           "económicas, legales y de otra índole?",
         ok="El empleador.",
         mal=["Los brigadistas designados.", "El Comité de Seguridad y Salud en el Trabajo.", "El trabajador accidentado."],
         fb="La Ley 29783 pone la responsabilidad en el empleador. Por eso la Alta Gerencia debe liderar, aprobar y dotar de recursos "
            "al plan. El art. 83 del Reglamento (DS 005-2012-TR, y modificatorias) exige disposiciones de prevención, "
            "preparación y respuesta ante emergencias."),
    dict(id=3, mod=1, tema="Capacidad de reacción y cuellos de botella",
         q="En la evacuación de Pachakuti se estima un tiempo requerido de salida de 310 s (detección 40 + alarma 30 + "
           "pre-movimiento 90 + desplazamiento 150) y el humo vuelve insostenible el pasillo a los 300 s. "
           "¿Cuál es la lectura correcta?",
         ok="Hay un déficit de 10 s; conviene actuar sobre las demoras reducibles, en especial el pre-movimiento "
            "(alarma clara, guías de evacuación, entrenamiento).",
         mal=["Hay un margen de 10 s; no hace falta intervenir.",
              "Hay un déficit de 10 s y la única solución es ampliar la escalera.",
              "Los dos tiempos no son comparables."],
         fb="Se compara el tiempo requerido de salida (RSET) con el disponible (ASET). Si RSET > ASET hay déficit. El pre-movimiento "
            "suele ser el componente más reducible con alarma efectiva, guías y práctica. Los números del caso son ficticios."),
    dict(id=4, mod=2, tema="Sistemas de protección",
         q="¿Cuál es un ejemplo de protección PASIVA contra incendios?",
         ok="La compartimentación con elementos resistentes al fuego.",
         mal=["Los rociadores automáticos.", "La bomba contra incendios.", "Los detectores de humo."],
         fb="La protección pasiva está integrada a la edificación y actúa sin accionarse (compartimentación, resistencia estructural, "
            "rutas protegidas). La activa requiere detección o accionamiento: rociadores, bombas, alarmas."),
    dict(id=5, mod=2, tema="Manejo de crisis y vocería",
         q="Un video de una nube de amoníaco en la planta se vuelve viral y los medios llaman a Pachakuti. "
           "¿Cuál es la mejor práctica de comunicación?",
         ok="Un vocero designado emite un mensaje inicial breve con hechos verificados, empatía con los afectados y un canal de actualización.",
         mal=["Que cada gerente responda según su criterio.",
              "Negar el incidente hasta tener toda la información.",
              "No responder para no empeorar la situación."],
         fb="Un vocero único, mensajes con hechos verificados, empatía y actualizaciones periódicas protegen la confianza. "
            "Negar o callar suele agravar la crisis y deja el relato en manos de terceros."),
    dict(id=6, mod=2, tema="Brigadas y respuesta ante materiales peligrosos",
         q="Hay un derrame de un químico peligroso en el almacén y la brigada interna solo tiene capacitación básica. "
           "¿Quién debe ingresar a la zona caliente?",
         ok="Solo personal entrenado en materiales peligrosos y con el equipo de protección que indique la hoja de datos de seguridad "
            "(por ejemplo, equipos especializados del CGBVP).",
         mal=["Cualquier brigadista voluntario.",
              "El jefe de turno con una mascarilla simple.",
              "Quien mejor conozca la planta."],
         fb="La brigada interna con capacitación básica actúa de forma defensiva: alertar, aislar, evacuar e informar. El ingreso a la "
            "zona caliente se reserva a personal entrenado y equipado. La HDS orienta peligros y protección."),
    dict(id=7, mod=2, tema="Continuidad del negocio (BCP)",
         q="En un análisis de impacto al negocio (BIA), ¿qué significa RTO?",
         ok="Tiempo objetivo de recuperación: plazo en que un proceso o servicio debe restablecerse tras la interrupción.",
         mal=["Máxima pérdida de datos aceptable.",
              "Nivel de riesgo operativo.",
              "Registro de trabajos de operación."],
         fb="RTO es el tiempo objetivo de recuperación. La máxima pérdida de datos aceptable es el RPO. La ISO 22301:2019 "
            "(con su Enmienda 1:2024) especifica los requisitos de un sistema de gestión de continuidad del negocio."),
    dict(id=8, mod=3, tema="Ingeniería de simulacros",
         q="Pachakuti quiere probar las decisiones de su comité de crisis sin movilizar personal ni equipos. "
           "¿Qué tipo de ejercicio es el más adecuado?",
         ok="Un ejercicio de gabinete (de mesa).",
         mal=["Un simulacro a gran escala.",
              "Un ejercicio funcional con movilización de brigadas.",
              "Una inspección de seguridad."],
         fb="El ejercicio de gabinete es una discusión guiada de un escenario, sin movilizar recursos: ideal para probar decisiones, "
            "roles y comunicaciones. Los funcionales y a gran escala movilizan personas y equipos."),
    dict(id=9, mod=3, tema="Comando de incidentes y coordinación externa",
         q="Llegan al lugar el CGBVP y la Policía Nacional. ¿Cuál es la lógica del Comando Unificado?",
         ok="Las instituciones comparten objetivos y estrategia comunes y coordinan en un mismo sistema de comando, cada una según sus competencias.",
         mal=["La empresa cede toda decisión y se retira del lugar.",
              "Cada institución actúa por separado y se informa al final.",
              "Solo la Policía Nacional asume el mando de todo."],
         fb="En Comando Unificado, cada institución conserva su competencia pero define con las demás objetivos y prioridades comunes, "
            "evitando órdenes contradictorias."),
    dict(id=10, mod=3, tema="Lecciones aprendidas y mejora",
         q="Tras controlar la emergencia, ¿qué hace que una lección aprendida realmente cierre el ciclo de mejora?",
         ok="Acciones correctivas con responsable, plazo y seguimiento, y verificación de su eficacia.",
         mal=["Un informe extenso que se archiva.",
              "Identificar y sancionar al culpable.",
              "Esperar a la auditoría anual para revisarlo."],
         fb="Sin responsable, fecha y verificación, una acción no es trazable. El informe post-evento alimenta el plan de mejora "
            "y la revisión por la dirección."),
]
N = len(QS)
MAX = N * PUNTOS_POR_PREGUNTA

MENSAJES = {
    "Avanzado": ("🥇", "¡Felicitaciones! Llegas con una base sólida. Tu desafío será profundizar en decisiones complejas, "
                       "KPIs y coordinación; tu experiencia enriquecerá los debates de caso."),
    "Intermedio": ("🥈", "¡Muy bien! Dominas varios conceptos clave. Con las sesiones del curso consolidarás lo que "
                         "falta y pasarás de conocer a decidir con criterio."),
    "Básico": ("🥉", "¡Buen punto de partida! Esta evaluación no tiene nota: sirve para ubicar dónde reforzar. "
                     "Lo que hoy es nuevo será herramienta en pocas sesiones. ¡Tú puedes!"),
}


def nivel_de(p):
    if p >= UMBRAL_AVANZADO:
        return "Avanzado"
    if p >= UMBRAL_INTERMEDIO:
        return "Intermedio"
    return "Básico"


# ── Base de datos ──────────────────────────────────────────────────────────────
def db_exec(sql, params=()):
    with closing(sqlite3.connect(DB, check_same_thread=False)) as c:
        c.execute(sql, params)
        c.commit()


def init_db():
    cols = ", ".join(f"q{i} INTEGER" for i in range(1, N + 1))
    db_exec(f"""CREATE TABLE IF NOT EXISTS ed(
        id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, alumno TEXT, intento INTEGER,
        puntaje REAL, nivel TEXT, tiempo_s INTEGER, {cols})""")


def leer():
    with closing(sqlite3.connect(DB)) as c:
        return pd.read_sql_query("SELECT * FROM ed", c)


def guardar(ss, puntaje, nivel, tiempo):
    df = leer()
    previos = 0 if df.empty else int((df.alumno.str.lower() == ss.alumno.lower()).sum())
    oks = [int(ss.resp.get(i) == QS[i]["ok"]) for i in range(N)]
    cols = ", ".join(f"q{i}" for i in range(1, N + 1))
    ph = ", ".join("?" * (6 + N))
    db_exec(f"INSERT INTO ed(ts,alumno,intento,puntaje,nivel,tiempo_s,{cols}) VALUES({ph})",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ss.alumno, previos + 1, puntaje, nivel,
             int(tiempo), *oks))


init_db()
ss = st.session_state
ss.setdefault("fase", "inicio")


# ── Pantallas ──────────────────────────────────────────────────────────────────
def pantalla_inicio():
    st.title("🧭 Evaluación Diagnóstica")
    st.subheader("Preparación y Respuesta a Emergencias · Maestría en PRL")
    st.markdown(f"""<div class="card">
<b>{N} preguntas · {MAX} puntos</b>. No tiene calificación: nos ayuda a conocer tus saberes previos.<br>
Verás el puntaje, el feedback de cada pregunta y tu nivel (<b>Básico, Intermedio o Avanzado</b>) al finalizar.
</div>
<div class="ficticio">Los casos usan una empresa ficticia (Industrias Alimentarias Pachakuti S.A.C.) con datos inventados para la enseñanza.</div>
""", unsafe_allow_html=True)
    st.write("")
    with st.form("f_inicio"):
        nombre = st.text_input("Tu nombre")
        ok = st.form_submit_button("▶ Comenzar evaluación", type="primary")
    if ok:
        if not nombre.strip():
            st.error("Ingresa tu nombre.")
            return
        ss.alumno = nombre.strip()
        ss.resp, ss.q, ss.t0 = {}, 0, time.time()
        rng = random.Random(time.time())
        ss.orden = []
        for q in QS:
            ops = [q["ok"]] + q["mal"]
            rng.shuffle(ops)
            ss.orden.append(ops)
        ss.celebrado = False
        ss.fase = "preguntas"
        st.rerun()


def pantalla_pregunta():
    i = ss.q
    q = QS[i]
    t = int(time.time() - ss.t0)
    st.caption(f"{ss.alumno} · ⏱ {t // 60:02d}:{t % 60:02d} · respondidas: {len(ss.resp)}/{N}")
    st.progress(i / N, text=f"Pregunta {i + 1} de {N}")
    st.markdown(f"<div class='card'><b>{MODULOS[q['mod']]}</b> · {q['tema']}</div>", unsafe_allow_html=True)
    st.markdown(f"### {i + 1}. {q['q']}")
    ops = ss.orden[i]
    previo = ss.resp.get(i)
    idx = ops.index(previo) if previo in ops else None
    sel = st.radio("Elige una opción", ops, index=idx, key=f"rad_{i}", label_visibility="collapsed")
    c1, c2, _ = st.columns([1, 1, 2])
    if c1.button("◀ Anterior", disabled=(i == 0)):
        if sel is not None:
            ss.resp[i] = sel
        ss.q -= 1
        st.rerun()
    ultima = i == N - 1
    if c2.button("Finalizar ✔" if ultima else "Siguiente ▶", type="primary"):
        if sel is None:
            st.error("Elige una opción para continuar.")
            return
        ss.resp[i] = sel
        if ultima:
            faltan = [k + 1 for k in range(N) if k not in ss.resp]
            if faltan:
                st.error(f"Aún faltan las preguntas: {faltan}")
                ss.q = faltan[0] - 1
                st.rerun()
            puntaje = sum(PUNTOS_POR_PREGUNTA for k in range(N) if ss.resp[k] == QS[k]["ok"])
            tiempo = int(time.time() - ss.t0)
            ss.final = dict(p=puntaje, nivel=nivel_de(puntaje), t=tiempo)
            guardar(ss, puntaje, ss.final["nivel"], tiempo)
            ss.fase = "resultado"
        else:
            ss.q += 1
        st.rerun()


def reporte_txt(f):
    lin = [f"Evaluación Diagnóstica · Preparación y Respuesta a Emergencias",
           f"Estudiante: {ss.alumno} | Puntaje: {f['p']}/{MAX} | Nivel: {f['nivel']} | Tiempo: {f['t']} s", ""]
    for k, q in enumerate(QS):
        ok = ss.resp[k] == q["ok"]
        lin += [f"{k + 1}. [{'OK' if ok else 'REFORZAR'}] {q['tema']}", f"   Tu respuesta: {ss.resp[k]}",
                f"   Correcta: {q['ok']}", f"   {q['fb']}", ""]
    return "\n".join(lin)


def pantalla_resultado():
    f = ss.final
    icono, msg = MENSAJES[f["nivel"]]
    st.title("🎉 Tus resultados")
    st.markdown(f"<div class='score'>{f['p']} / {MAX}</div>", unsafe_allow_html=True)
    st.write("")
    st.markdown(f"<span class='nivel'>{icono} Nivel {f['nivel']}</span>", unsafe_allow_html=True)
    st.markdown(f"<div class='card' style='margin-top:14px'>{msg}</div>", unsafe_allow_html=True)
    if not ss.get("celebrado"):
        if f["nivel"] == "Avanzado":
            st.balloons()
        st.toast(f"{icono} ¡Nivel {f['nivel']}!")
        ss.celebrado = True
    st.caption(f"Tiempo total: {f['t'] // 60} min {f['t'] % 60} s")

    st.subheader("Por módulo")
    reforzar = []
    for m in (1, 2, 3):
        idx = [k for k, q in enumerate(QS) if q["mod"] == m]
        ac = sum(ss.resp[k] == QS[k]["ok"] for k in idx)
        pct = ac / len(idx)
        etiqueta = "💪 Fortaleza" if pct >= 0.6 else "🎯 A reforzar"
        if pct < 0.6:
            reforzar.append(m)
        st.markdown(f"**{MODULOS[m]}** — {ac}/{len(idx)} · {etiqueta}")
        st.progress(pct)
    if reforzar:
        st.info("Presta especial atención a: " + "; ".join(f"Módulo {m} ({SESIONES[m]})" for m in reforzar) + ".")
    else:
        st.success("Tu desempeño es parejo en los tres módulos. ¡Excelente base!")

    st.subheader("Feedback por pregunta")
    for k, q in enumerate(QS):
        ok = ss.resp[k] == q["ok"]
        with st.expander(f"{'✅' if ok else '❌'} {k + 1}. {q['tema']}"):
            st.write(f"**Tu respuesta:** {ss.resp[k]}")
            if not ok:
                st.write(f"**Respuesta correcta:** {q['ok']}")
            st.write(q["fb"])

    df = leer()
    if not df.empty:
        st.subheader("Tu aula (anónimo)")
        cuenta = df.nivel.value_counts().reindex(["Avanzado", "Intermedio", "Básico"]).fillna(0).astype(int)
        c1, c2, c3 = st.columns(3)
        c1.metric("🥇 Avanzado", int(cuenta["Avanzado"]))
        c2.metric("🥈 Intermedio", int(cuenta["Intermedio"]))
        c3.metric("🥉 Básico", int(cuenta["Básico"]))

    st.download_button("⬇ Descargar mi reporte (.txt)", reporte_txt(f).encode("utf-8"),
                       file_name="mi_diagnostico.txt", mime="text/plain")
    if st.button("Hacer otro intento"):
        for k in ["fase", "resp", "q", "t0", "orden", "final", "celebrado"]:
            ss.pop(k, None)
        for k in list(ss.keys()):
            if str(k).startswith("rad_"):
                del ss[k]
        st.rerun()


# ── Panel instructor ───────────────────────────────────────────────────────────
def instructor_pw():
    try:
        return st.secrets["INSTRUCTOR_PASSWORD"]
    except Exception:
        return os.environ.get("INSTRUCTOR_PASSWORD", "pachakuti2026")


def panel_instructor():
    st.title("🔐 Panel de instructor")
    if not ss.get("inst_ok"):
        pw = st.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
            if pw == instructor_pw():
                ss.inst_ok = True
                st.rerun()
            else:
                st.error("Contraseña incorrecta.")
        st.caption("Define INSTRUCTOR_PASSWORD en st.secrets o como variable de entorno; cambia la contraseña por defecto.")
        return
    df = leer()
    if df.empty:
        st.info("Aún no hay respuestas.")
        return
    solo1 = st.checkbox("Solo primer intento de cada estudiante", value=True)
    if solo1:
        df = df[df.intento == 1]
    c1, c2, c3 = st.columns(3)
    c1.metric("Participantes", df.alumno.nunique())
    c2.metric("Promedio", f"{df.puntaje.mean():.1f} / {MAX}")
    c3.metric("Tiempo prom.", f"{df.tiempo_s.mean() / 60:.1f} min")

    st.subheader("Distribución por nivel")
    st.bar_chart(df.nivel.value_counts().reindex(["Básico", "Intermedio", "Avanzado"]).fillna(0))

    st.subheader("% de acierto por pregunta (¿qué saben y qué no?)")
    pq = pd.DataFrame({f"P{q['id']} (M{q['mod']}) {q['tema']}": [df[f"q{q['id']}"].mean() * 100] for q in QS}).T
    pq.columns = ["% acierto"]
    st.bar_chart(pq)

    st.subheader("% de acierto por módulo")
    filas = []
    for m in (1, 2, 3):
        qs = [f"q{q['id']}" for q in QS if q["mod"] == m]
        filas.append({"Módulo": MODULOS[m], "% acierto": round(df[qs].mean().mean() * 100, 1)})
    st.dataframe(pd.DataFrame(filas))

    st.subheader("Detalle")
    st.dataframe(df)
    st.download_button("⬇ Exportar CSV", df.to_csv(index=False).encode("utf-8-sig"),
                       file_name=f"diagnostica_{datetime.now():%Y%m%d_%H%M}.csv", mime="text/csv")
    with st.expander("Zona de riesgo"):
        conf = st.checkbox("Confirmo que quiero borrar todas las respuestas")
        if st.button("Borrar todo", disabled=not conf):
            db_exec("DELETE FROM ed")
            st.rerun()
    if st.button("Cerrar sesión de instructor"):
        ss.inst_ok = False
        st.rerun()


# ── Enrutado ───────────────────────────────────────────────────────────────────
with st.sidebar:
    vista = st.radio("Vista", ["Estudiante", "Instructor"])

if vista == "Instructor":
    panel_instructor()
elif ss.fase == "inicio":
    pantalla_inicio()
elif ss.fase == "preguntas":
    pantalla_pregunta()
else:
    pantalla_resultado()
