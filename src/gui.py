"""
gui.py — Interface de configuração do CV Engine
Autor: Guivieira26

Tecnologia: PySide6
Funcionalidades:
- Manete DualShock desenhada em SVG clicável (hot-spots por ação)
- Pop-up de seleção de gesto com ícones SVG, abas ESQ/DIR e checkboxes de categoria
- Gesto atual pré-selecionado ao reabrir o pop-up
- Opção de limpar mapeamento de um botão específico ou todos
- Toggle de inversão do eixo X do nariz
- Botão para salvar config.json e iniciar engine.py
"""

import json
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore    import Qt, QByteArray, QSize, Signal
from PySide6.QtGui     import QPixmap, QIcon, QPainter, QFont
from PySide6.QtSvg     import QSvgRenderer
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QDialog, QScrollArea, QGridLayout, QVBoxLayout, QHBoxLayout,
    QCheckBox, QTabWidget, QGroupBox, QMessageBox, QStatusBar,
    QToolButton,
)

from gestos_icones import ICONES, CATEGORIAS, listar_todos

# =============================================================================
# CAMINHOS
# =============================================================================

BASE_DIR    = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.json"
ENGINE_PATH = BASE_DIR / "engine.py"

# =============================================================================
# HELPERS — SVG → QPixmap / QIcon
# =============================================================================

def svg_para_pixmap(svg_str: str, w: int = 64, h: int = 64) -> QPixmap:
    renderer = QSvgRenderer(QByteArray(svg_str.encode()))
    pixmap   = QPixmap(w, h)
    pixmap.fill(Qt.transparent)
    painter  = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return pixmap


def svg_para_icon(svg_str: str, size: int = 64) -> QIcon:
    return QIcon(svg_para_pixmap(svg_str, size, size))

# =============================================================================
# AÇÕES DO CONTROLE
# =============================================================================

ACOES_LABELS: dict[str, str] = {
    "BTN_A":          "Botão A (✕)",
    "BTN_B":          "Botão B (○)",
    "BTN_X":          "Botão X (□)",
    "BTN_Y":          "Botão Y (△)",
    "BTN_LB":         "Bumper L1",
    "BTN_RB":         "Bumper R1",
    "BTN_START":      "Start",
    "BTN_SELECT":     "Select",
    "BTN_L3":         "L3 (click analógico esq)",
    "BTN_R3":         "R3 (click analógico dir)",
    "GATILHO_LT":     "Gatilho L2",
    "GATILHO_RT":     "Gatilho R2",
    "DPAD_CIMA":      "D-Pad ↑",
    "DPAD_BAIXO":     "D-Pad ↓",
    "DPAD_ESQ":       "D-Pad ←",
    "DPAD_DIR":       "D-Pad →",
    "ANALOG_ESQ_CIMA":  "Analógico Esq ↑",
    "ANALOG_ESQ_BAIXO": "Analógico Esq ↓",
    "ANALOG_ESQ_ESQ":   "Analógico Esq ←",
    "ANALOG_ESQ_DIR":   "Analógico Esq →",
}

# =============================================================================
# HOT-SPOTS DA MANETE (coordenadas em pixels sobre canvas 520x340)
# =============================================================================

HOTSPOTS: dict[str, tuple] = {
    "BTN_A":           ("✕",   380, 210, 16),
    "BTN_B":           ("○",   405, 188, 16),
    "BTN_X":           ("□",   355, 188, 16),
    "BTN_Y":           ("△",   380, 165, 16),
    "BTN_LB":          ("L1",  136,  98, 18),
    "BTN_RB":          ("R1",  384,  98, 18),
    "GATILHO_LT":      ("L2",  134,  78, 18),
    "GATILHO_RT":      ("R2",  386,  78, 18),
    "BTN_START":       ("STA", 295, 184, 13),
    "BTN_SELECT":      ("SEL", 225, 184, 13),
    "DPAD_CIMA":       ("↑",   145, 175, 11),
    "DPAD_BAIXO":      ("↓",   145, 215, 11),
    "DPAD_ESQ":        ("←",   123, 195, 11),
    "DPAD_DIR":        ("→",   167, 195, 11),
    "ANALOG_ESQ_CIMA": ("↑",   215, 222, 10),
    "ANALOG_ESQ_BAIXO":("↓",   215, 258, 10),
    "ANALOG_ESQ_ESQ":  ("←",   197, 240, 10),
    "ANALOG_ESQ_DIR":  ("→",   233, 240, 10),
    "BTN_L3":          ("L3",  215, 240, 20),
    "BTN_R3":          ("R3",  325, 240, 20),
}

# =============================================================================
# HOT-SPOT BUTTON
# =============================================================================

class HotspotButton(QPushButton):
    def __init__(self, label: str, cx: int, cy: int, raio: int, parent=None):
        super().__init__(parent)
        self._label = label
        self._raio  = raio
        self._gesto_esq: str | None = None
        self._gesto_dir: str | None = None
        d = raio * 2
        self.setGeometry(cx - raio, cy - raio, d, d)
        self.setToolTip(label)
        self._refresh()

    def definir_gestos(self, esq: str | None, dir_: str | None) -> None:
        self._gesto_esq = esq
        self._gesto_dir = dir_
        self._refresh()

    def _refresh(self) -> None:
        mapeado = bool(self._gesto_esq or self._gesto_dir)
        borda   = "#00c875" if mapeado else "#444466"
        fundo   = "rgba(0,200,117,40)" if mapeado else "rgba(255,255,255,15)"
        r       = self._raio
        self.setStyleSheet(f"""
            QPushButton {{
                border-radius: {r}px; border: 2px solid {borda};
                background: {fundo}; color: #ccccee; font-size: 8px; font-weight: bold;
            }}
            QPushButton:hover {{ background: rgba(0,200,117,70); border-color: #00e890; }}
        """)
        txt = self._label
        if mapeado:
            partes = []
            if self._gesto_esq: partes.append(self._gesto_esq[:7])
            if self._gesto_dir: partes.append(self._gesto_dir[:7])
            txt = "\n".join(partes)
        self.setText(txt)

# =============================================================================
# CARD DE GESTO (pop-up)
# =============================================================================

class GestoCard(QToolButton):
    selecionado = Signal(str)

    def __init__(self, nome: str, parent=None):
        super().__init__(parent)
        self.nome = nome
        self.setCheckable(True)
        self.setFixedSize(100, 110)
        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.setIconSize(QSize(60, 60))

        svg = ICONES.get(nome, "")
        if svg:
            self.setIcon(svg_para_icon(svg, 60))

        self.setText(nome.replace("_", "\n").lower())
        self.setFont(QFont("Segoe UI", 7))
        self._estilo_normal()
        self.clicked.connect(lambda: self.selecionado.emit(self.nome))

    def marcar(self, ativo: bool) -> None:
        self.setChecked(ativo)
        if ativo:
            self._estilo_selecionado()
        else:
            self._estilo_normal()

    def _estilo_normal(self):
        self.setStyleSheet("""
            QToolButton { border:1.5px solid #333355; border-radius:8px;
                          background:#1a1a2e; color:#8888aa; padding:4px; }
            QToolButton:hover { border-color:#5555aa; background:#22224a; }
        """)

    def _estilo_selecionado(self):
        self.setStyleSheet("""
            QToolButton { border:2px solid #00c875; border-radius:8px;
                          background:#0d2b1f; color:#00e890; padding:4px; }
        """)

# =============================================================================
# POP-UP DE SELEÇÃO DE GESTO
# =============================================================================

class PopupGesto(QDialog):
    def __init__(self, acao_key: str, gesto_esq_atual: str | None,
                 gesto_dir_atual: str | None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Mapear: {ACOES_LABELS.get(acao_key, acao_key)}")
        self.setMinimumSize(660, 580)
        self.setStyleSheet("QDialog{background:#12121e;} QLabel{color:#ccccee;}")

        self._resultado: tuple | None = None
        self._esq_atual = gesto_esq_atual
        self._dir_atual = gesto_dir_atual
        self._cards_esq: dict[str, GestoCard] = {}
        self._cards_dir: dict[str, GestoCard] = {}

        raiz = QVBoxLayout(self)
        raiz.setSpacing(8)

        # Cabeçalho
        lbl = QLabel(f"Gesto para: <b>{ACOES_LABELS.get(acao_key, acao_key)}</b>")
        lbl.setStyleSheet("font-size:14px; color:#fff; padding:4px 0;")
        raiz.addWidget(lbl)

        # Filtros
        grp = QGroupBox("Filtrar por categoria")
        grp.setStyleSheet("""
            QGroupBox{border:1px solid #333355;border-radius:6px;margin-top:6px;
                      color:#9999bb;font-size:11px;padding-top:4px;}
            QGroupBox::title{subcontrol-origin:margin;left:8px;padding:0 4px;}
        """)
        lay_f = QHBoxLayout(grp)
        lay_f.setSpacing(4)
        self._checks: dict[str, QCheckBox] = {}
        for cat in CATEGORIAS:
            cb = QCheckBox(cat)
            cb.setStyleSheet("QCheckBox{color:#aaaacc;font-size:10px;}"
                             "QCheckBox::indicator{width:12px;height:12px;}")
            cb.stateChanged.connect(self._filtrar)
            self._checks[cat] = cb
            lay_f.addWidget(cb)
        lay_f.addStretch()
        btn_all = QPushButton("Todos")
        btn_all.setStyleSheet("QPushButton{color:#7777aa;border:none;font-size:10px;}"
                              "QPushButton:hover{color:#aaaaff;}")
        btn_all.clicked.connect(self._limpar_filtros)
        lay_f.addWidget(btn_all)
        raiz.addWidget(grp)

        # Abas
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet("""
            QTabWidget::pane{border:1px solid #333355;border-radius:4px;}
            QTabBar::tab{background:#1a1a2e;color:#8888aa;padding:6px 18px;
                         border:1px solid #333355;border-bottom:none;}
            QTabBar::tab:selected{background:#22224a;color:#fff;}
        """)
        self._scroll_esq, self._grid_esq = self._nova_aba()
        self._scroll_dir, self._grid_dir = self._nova_aba()
        self._tabs.addTab(self._scroll_esq, "✋  Mão Esquerda")
        self._tabs.addTab(self._scroll_dir, "🤚  Mão Direita")
        raiz.addWidget(self._tabs, 1)

        self._popular(listar_todos())

        # Rodapé
        rod = QHBoxLayout()
        self._lbl_sel = QLabel("Nenhum selecionado")
        self._lbl_sel.setStyleSheet("color:#00c875;font-size:12px;")
        rod.addWidget(self._lbl_sel)
        rod.addStretch()

        for txt, cor, slot in [
            ("Limpar", "#cc4444", self._limpar_mapeamento),
            ("Cancelar", "#666688", self.reject),
            ("Confirmar", "#00c875", self._confirmar),
        ]:
            b = QPushButton(txt)
            b.setStyleSheet(
                f"QPushButton{{color:#fff;background:{cor};border:none;"
                f"border-radius:4px;padding:5px 16px;font-weight:bold;}}"
                f"QPushButton:hover{{opacity:0.85;}}"
            )
            b.clicked.connect(slot)
            rod.addWidget(b)
        raiz.addLayout(rod)

        # Pré-selecionar
        if gesto_esq_atual and gesto_esq_atual in self._cards_esq:
            self._cards_esq[gesto_esq_atual].marcar(True)
        if gesto_dir_atual and gesto_dir_atual in self._cards_dir:
            self._cards_dir[gesto_dir_atual].marcar(True)
        self._atualizar_label()

    def _nova_aba(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;background:#12121e;}")
        cont = QWidget()
        cont.setStyleSheet("background:#12121e;")
        grid = QGridLayout(cont)
        grid.setSpacing(8)
        grid.setContentsMargins(12, 12, 12, 12)
        scroll.setWidget(cont)
        return scroll, grid

    def _popular(self, gestos: list[str]) -> None:
        for grid, cards, atual, prefixo in [
            (self._grid_esq, self._cards_esq, self._esq_atual, "ESQ"),
            (self._grid_dir, self._cards_dir, self._dir_atual, "DIR"),
        ]:
            while grid.count():
                w = grid.takeAt(0).widget()
                if w: w.deleteLater()
            cards.clear()

            for idx, nome in enumerate(gestos):
                card = GestoCard(nome)
                card.selecionado.connect(
                    lambda g, p=prefixo, d=cards: self._on_sel(g, p, d)
                )
                if nome == atual:
                    card.marcar(True)
                grid.addWidget(card, idx // 5, idx % 5)
                cards[nome] = card

    def _on_sel(self, nome: str, prefixo: str, cards: dict) -> None:
        for n, c in cards.items():
            c.marcar(n == nome)
        self._atualizar_label()

    def _atualizar_label(self) -> None:
        partes = []
        for p, cards in [("ESQ", self._cards_esq), ("DIR", self._cards_dir)]:
            s = next((n for n, c in cards.items() if c.isChecked()), None)
            if s: partes.append(f"{p}: {s}")
        self._lbl_sel.setText("  |  ".join(partes) or "Nenhum selecionado")

    def _filtrar(self) -> None:
        cats = [c for c, cb in self._checks.items() if cb.isChecked()]
        if not cats:
            self._popular(listar_todos())
            return
        vistos, resultado = set(), []
        for cat in cats:
            for g in CATEGORIAS.get(cat, []):
                if g not in vistos:
                    resultado.append(g)
                    vistos.add(g)
        self._popular(resultado)

    def _limpar_filtros(self) -> None:
        for cb in self._checks.values():
            cb.blockSignals(True)
            cb.setChecked(False)
            cb.blockSignals(False)
        self._popular(listar_todos())

    def _limpar_mapeamento(self) -> None:
        self._resultado = ("LIMPAR", "LIMPAR")
        self.accept()

    def _confirmar(self) -> None:
        esq = next((n for n, c in self._cards_esq.items() if c.isChecked()), None)
        dir_ = next((n for n, c in self._cards_dir.items() if c.isChecked()), None)
        self._resultado = (esq, dir_)
        self.accept()

    def resultado(self) -> tuple | None:
        return self._resultado

# =============================================================================
# WIDGET DA MANETE
# =============================================================================

_SVG_MANETE = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 520 340" width="520" height="340">
  <rect width="520" height="340" fill="#0e0e1a" rx="12"/>
  <!-- Corpo -->
  <path d="M100,200 Q80,280 140,310 Q200,340 260,330 Q320,340 380,310
           Q440,280 420,200 Q410,140 390,110 L390,80 Q390,60 370,55
           L310,50 Q290,48 270,52 L250,52 Q230,48 210,52
           L150,55 Q130,60 130,80 L130,110 Q110,140 100,200Z"
        fill="#1c1c2e" stroke="#333355" stroke-width="1.5"/>
  <!-- Alças -->
  <path d="M100,200 Q85,250 90,300 Q95,330 120,335 Q150,340 160,310 Q170,280 155,240 Q140,210 130,200Z"
        fill="#181828" stroke="#2a2a40" stroke-width="1"/>
  <path d="M420,200 Q435,250 430,300 Q425,330 400,335 Q370,340 360,310 Q350,280 365,240 Q380,210 390,200Z"
        fill="#181828" stroke="#2a2a40" stroke-width="1"/>
  <!-- D-Pad -->
  <rect x="128" y="180" width="34" height="10" rx="2" fill="#111122"/>
  <rect x="138" y="170" width="14" height="30" rx="2" fill="#111122"/>
  <!-- Analógicos -->
  <circle cx="215" cy="240" r="22" fill="#111122" stroke="#2a2a40" stroke-width="1"/>
  <circle cx="215" cy="240" r="13" fill="#0d0d1a"/>
  <circle cx="325" cy="240" r="22" fill="#111122" stroke="#2a2a40" stroke-width="1"/>
  <circle cx="325" cy="240" r="13" fill="#0d0d1a"/>
  <!-- Botões face -->
  <circle cx="380" cy="210" r="13" fill="#1a1a30" stroke="#cc4444" stroke-width="1.5"/>
  <text x="380" y="215" text-anchor="middle" font-size="11" fill="#cc4444" font-family="sans-serif">✕</text>
  <circle cx="405" cy="188" r="13" fill="#1a1a30" stroke="#4444cc" stroke-width="1.5"/>
  <text x="405" y="192" text-anchor="middle" font-size="11" fill="#6666ee" font-family="sans-serif">○</text>
  <circle cx="355" cy="188" r="13" fill="#1a1a30" stroke="#cc44cc" stroke-width="1.5"/>
  <text x="355" y="192" text-anchor="middle" font-size="11" fill="#cc44cc" font-family="sans-serif">□</text>
  <circle cx="380" cy="165" r="13" fill="#1a1a30" stroke="#44cc88" stroke-width="1.5"/>
  <text x="380" y="170" text-anchor="middle" font-size="11" fill="#44cc88" font-family="sans-serif">△</text>
  <!-- Bumpers -->
  <rect x="112" y="92" width="48" height="13" rx="6" fill="#222238" stroke="#333355" stroke-width="1"/>
  <text x="136" y="102" text-anchor="middle" font-size="9" fill="#8888aa" font-family="sans-serif">L1</text>
  <rect x="360" y="92" width="48" height="13" rx="6" fill="#222238" stroke="#333355" stroke-width="1"/>
  <text x="384" y="102" text-anchor="middle" font-size="9" fill="#8888aa" font-family="sans-serif">R1</text>
  <!-- Gatilhos -->
  <rect x="112" y="68" width="44" height="18" rx="7" fill="#2a2a3e" stroke="#444466" stroke-width="1"/>
  <text x="134" y="81" text-anchor="middle" font-size="9" fill="#7777aa" font-family="sans-serif">L2</text>
  <rect x="364" y="68" width="44" height="18" rx="7" fill="#2a2a3e" stroke="#444466" stroke-width="1"/>
  <text x="386" y="81" text-anchor="middle" font-size="9" fill="#7777aa" font-family="sans-serif">R2</text>
  <!-- Select/Start -->
  <rect x="213" y="178" width="22" height="11" rx="4" fill="#111122" stroke="#333355" stroke-width="1"/>
  <text x="224" y="187" text-anchor="middle" font-size="7" fill="#555577" font-family="sans-serif">SEL</text>
  <rect x="285" y="178" width="22" height="11" rx="4" fill="#111122" stroke="#333355" stroke-width="1"/>
  <text x="296" y="187" text-anchor="middle" font-size="7" fill="#555577" font-family="sans-serif">STA</text>
  <!-- Logo -->
  <circle cx="260" cy="192" r="13" fill="#111122" stroke="#333355" stroke-width="1"/>
  <text x="260" y="196" text-anchor="middle" font-size="8" fill="#555577" font-family="sans-serif">CV</text>
</svg>
"""


class ManeteWidget(QWidget):
    hotspot_clicado = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(520, 340)
        self._botoes: dict[str, HotspotButton] = {}

        # Fundo SVG
        renderer = QSvgRenderer(QByteArray(_SVG_MANETE.encode()))
        pm = QPixmap(520, 340)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        renderer.render(p)
        p.end()

        fundo = QLabel(self)
        fundo.setPixmap(pm)
        fundo.setGeometry(0, 0, 520, 340)

        # Hot-spots
        for key, (label, cx, cy, raio) in HOTSPOTS.items():
            btn = HotspotButton(label, cx, cy, raio, self)
            btn.clicked.connect(lambda checked=False, k=key: self.hotspot_clicado.emit(k))
            self._botoes[key] = btn

    def atualizar(self, key: str, esq: str | None, dir_: str | None) -> None:
        if key in self._botoes:
            self._botoes[key].definir_gestos(esq, dir_)

# =============================================================================
# JANELA PRINCIPAL
# =============================================================================

class JanelaPrincipal(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CV Engine — Configuração de Gestos")
        self.setMinimumSize(620, 520)
        self.setStyleSheet("""
            QMainWindow,QWidget{background:#0e0e1a;}
            QLabel{color:#ccccee;}
            QGroupBox{color:#9999bb;border:1px solid #333355;
                      border-radius:6px;margin-top:8px;font-size:11px;padding-top:6px;}
            QGroupBox::title{subcontrol-origin:margin;left:8px;padding:0 4px;}
        """)

        self._config: dict = {}
        self._carregar_config()

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(10)
        root.setContentsMargins(16, 14, 16, 8)

        # Título
        t = QLabel("CV Engine — Mapeamento de Gestos")
        t.setStyleSheet("font-size:17px;font-weight:bold;color:#fff;")
        root.addWidget(t)

        sub = QLabel("Clique num botão da manete para associar um gesto  ·  Verde = mapeado")
        sub.setStyleSheet("font-size:11px;color:#666688;margin-bottom:2px;")
        root.addWidget(sub)

        # Manete
        row = QHBoxLayout()
        row.addStretch()
        self._manete = ManeteWidget()
        self._manete.hotspot_clicado.connect(self._abrir_popup)
        row.addWidget(self._manete)
        row.addStretch()
        root.addLayout(row)

        # Opções
        grp = QGroupBox("Rosto (analógico direito — sempre reservado)")
        lay_op = QHBoxLayout(grp)
        self._cb_inv = QCheckBox("Inverter eixo X do nariz")
        self._cb_inv.setStyleSheet("color:#aaaacc;font-size:12px;")
        self._cb_inv.setChecked(bool(self._config.get("inverter_x_rosto", False)))
        lay_op.addWidget(self._cb_inv)
        lay_op.addStretch()
        dica = QLabel("Dupla PINCA_INDICADOR simultânea = recalibrar centro")
        dica.setStyleSheet("color:#444466;font-size:11px;font-style:italic;")
        lay_op.addWidget(dica)
        root.addWidget(grp)

        # Botões
        lay_btn = QHBoxLayout()
        lay_btn.addStretch()

        for txt, cor, slot in [
            ("Limpar tudo",        "#8a2020", self._limpar_tudo),
            ("💾 Salvar",          "#1a5c3a", self._salvar),
            ("▶ Iniciar Engine",  "#1a3a6c", self._iniciar),
        ]:
            b = QPushButton(txt)
            b.setStyleSheet(
                f"QPushButton{{color:#fff;background:{cor};border:none;"
                f"border-radius:5px;padding:6px 18px;font-size:12px;font-weight:bold;}}"
                f"QPushButton:hover{{filter:brightness(1.2);}}"
            )
            b.clicked.connect(slot)
            lay_btn.addWidget(b)

        root.addLayout(lay_btn)

        self._status = QStatusBar()
        self._status.setStyleSheet("QStatusBar{color:#556677;font-size:11px;background:#0e0e1a;}")
        self.setStatusBar(self._status)
        self._status.showMessage("Pronto. Clique num botão da manete para configurar.")

        self._refresh_todos()

    # ── Config ───────────────────────────────────────────────────────────────

    def _carregar_config(self) -> None:
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                self._config = json.load(f)

    def _descrever_lado(self, key: str) -> str:
        if key.startswith("ESQ_"):
            return "mão esquerda"
        if key.startswith("DIR_"):
            return "mão direita"
        return "lado desconhecido"

    def _validar_conflitos(self, config: dict) -> list[str]:
        """
        Retorna conflitos apenas quando houver colisão real no mesmo lado.

        O mesmo gesto pode existir nas duas mãos ao mesmo tempo. O que não
        pode acontecer é o mesmo hot-spot/lado acabar com mais de um gesto,
        ou um mesmo gesto ser reutilizado dentro do mesmo lado em dois lugares.
        """
        vistos_por_lado: dict[str, dict[str, str]] = {"ESQ": {}, "DIR": {}}
        conflitos: list[str] = []

        for k, v in config.items():
            if not (isinstance(k, str) and (k.startswith("ESQ_") or k.startswith("DIR_"))):
                continue
            if not isinstance(v, str):
                continue

            lado = "ESQ" if k.startswith("ESQ_") else "DIR"
            vistos = vistos_por_lado[lado]

            # Mesma ação repetida no mesmo lado = conflito real.
            if v in vistos:
                conflitos.append(
                    f"No lado {self._descrever_lado(k)}, a ação {v} já está usada por {vistos[v]} e também por {k}."
                )
                continue

            vistos[v] = k

        return conflitos

    def _salvar(self) -> None:
        self._config["inverter_x_rosto"] = self._cb_inv.isChecked()
        limpo = {k: v for k, v in self._config.items() if not k.startswith("_")}
        limpo["_comentario"] = "ESQ_/DIR_ + nome_gesto → ação_controle"

        conflitos = self._validar_conflitos(limpo)
        if conflitos:
            QMessageBox.warning(
                self,
                "Conflito de mapeamento",
                "Não foi possível salvar porque a mesma ação foi atribuída a mais de um gesto:\n\n"
                + "\n".join(f"- {msg}" for msg in conflitos),
            )
            self._status.showMessage("Salvamento bloqueado por conflito de mapeamento.")
            return

        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(limpo, f, indent=2, ensure_ascii=False)
        self._status.showMessage(f"Salvo → {CONFIG_PATH}")
        QMessageBox.information(self, "Salvo", f"config.json salvo em:\n{CONFIG_PATH}")

    # ── Hot-spots ─────────────────────────────────────────────────────────────

    def _refresh_todos(self) -> None:
        for key in HOTSPOTS:
            self._manete.atualizar(
                key,
                self._config.get(f"ESQ_{key}"),
                self._config.get(f"DIR_{key}"),
            )

    def _abrir_popup(self, key: str) -> None:
        popup = PopupGesto(
            key,
            self._config.get(f"ESQ_{key}"),
            self._config.get(f"DIR_{key}"),
            self,
        )
        if popup.exec() != QDialog.Accepted:
            return

        res = popup.resultado()
        if not res:
            return

        sel_esq, sel_dir = res

        if sel_esq == "LIMPAR":
            self._config.pop(f"ESQ_{key}", None)
            self._config.pop(f"DIR_{key}", None)
        else:
            for prefixo, sel in [("ESQ", sel_esq), ("DIR", sel_dir)]:
                cfg_key = f"{prefixo}_{key}"
                if sel:
                    self._config[cfg_key] = sel
                else:
                    self._config.pop(cfg_key, None)

        self._manete.atualizar(
            key,
            self._config.get(f"ESQ_{key}"),
            self._config.get(f"DIR_{key}"),
        )
        label = ACOES_LABELS.get(key, key)
        self._status.showMessage(
            f"{label} → ESQ: {self._config.get(f'ESQ_{key}','—')}  "
            f"DIR: {self._config.get(f'DIR_{key}','—')}"
        )

    # ── Ações ─────────────────────────────────────────────────────────────────

    def _limpar_tudo(self) -> None:
        if QMessageBox.question(
            self, "Limpar tudo", "Remover todos os mapeamentos?",
            QMessageBox.Yes | QMessageBox.No,
        ) == QMessageBox.Yes:
            self._config = {"inverter_x_rosto": self._cb_inv.isChecked()}
            self._refresh_todos()
            self._status.showMessage("Todos os mapeamentos removidos.")

    # def _iniciar(self) -> None:
    #     self._salvar()
    #     if not ENGINE_PATH.exists():
    #         QMessageBox.warning(self, "Não encontrado", f"engine.py não encontrado:\n{ENGINE_PATH}")
    #         return
    #     subprocess.Popen([sys.executable, str(ENGINE_PATH)])
    #     self._status.showMessage("Engine iniciado.")

    def _iniciar(self) -> None:
        self._salvar()
        import sys, os, subprocess

        # Dentro do bundle PyInstaller, sys.frozen = True
        # O próprio .exe é relançado com --engine para rodar o engine
        if getattr(sys, "frozen", False):
            exe = sys.executable
            subprocess.Popen([exe, "--engine"])
        else:
            # Desenvolvimento normal: chama engine.py diretamente
            subprocess.Popen([sys.executable, str(ENGINE_PATH)])
        self._status.showMessage("Engine iniciado.")


# =============================================================================
# ENTRY POINT
# =============================================================================

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = JanelaPrincipal()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    import sys
    if "--engine" in sys.argv:
        # Modo engine: importa e roda o engine direto, sem GUI
        from engine import main as engine_main
        engine_main()
    else:
        # Modo GUI normal
        main()