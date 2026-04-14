from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from mimetypes import guess_type
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

from .service import FontAgentService
from .use_cases import get_use_case_preset


INDEX_HTML = """<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>FontAgent</title>
  <style>
    :root {
      --bg: #f3ecdf;
      --panel: #fffdfa;
      --line: #d9cfbd;
      --ink: #1e1811;
      --muted: #796d5c;
      --accent: #845e3b;
      --accent-soft: #eee2ce;
      --shadow: 0 18px 48px rgba(60, 44, 20, 0.08);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Georgia, "Apple SD Gothic Neo", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, #faf5ea 0%, rgba(250,245,234,0) 35%),
        radial-gradient(circle at top right, #efe4cf 0%, rgba(239,228,207,0) 30%),
        var(--bg);
    }
    a { color: inherit; }
    .page { max-width: 1680px; margin: 0 auto; padding: 24px 18px 56px; }
    .hero {
      display: grid;
      grid-template-columns: 1fr;
      margin-bottom: 18px;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 24px;
      padding: 20px;
      box-shadow: var(--shadow);
    }
    .eyebrow {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 12px;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.14em;
      color: var(--muted);
    }
    .hero-copy h1 {
      margin: 0 0 10px;
      font-size: clamp(42px, 4.8vw, 72px);
      line-height: 0.94;
      letter-spacing: -0.04em;
    }
    .hero-copy p,
    .panel p {
      margin: 0;
      color: var(--muted);
      line-height: 1.58;
    }
    .workflow-strip {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
      margin-top: 18px;
    }
    .workflow-card {
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 14px;
      background: rgba(255,255,255,0.75);
    }
    .workflow-card strong {
      display: block;
      font-size: 12px;
      color: var(--muted);
      margin-bottom: 6px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }
    .workflow-card span {
      display: block;
      font-size: 14px;
      font-weight: 600;
      line-height: 1.45;
    }
    .workspace {
      display: grid;
      grid-template-columns: 320px minmax(0, 1fr);
      gap: 18px;
      align-items: start;
    }
    .rail {
      display: grid;
      gap: 18px;
      position: sticky;
      top: 18px;
    }
    .section-title {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      gap: 12px;
      margin-bottom: 14px;
    }
    .section-title h2,
    .section-title h3 {
      margin: 0;
      font-size: 20px;
      line-height: 1.1;
    }
    .section-title span {
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }
    .controls { display: grid; gap: 12px; }
    .quick-preset-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }
    .preset-chip {
      display: grid;
      gap: 6px;
      align-content: start;
      text-align: left;
      min-height: 96px;
      padding: 14px;
      border-radius: 18px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.78);
      color: var(--ink);
      cursor: pointer;
    }
    .preset-chip strong {
      display: block;
      font-size: 13px;
      line-height: 1.25;
    }
    .preset-chip span {
      display: block;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.45;
    }
    .preset-chip.active {
      border-color: var(--ink);
      background: linear-gradient(180deg, #fff9ee 0%, #f6e8d0 100%);
      box-shadow: inset 0 0 0 1px rgba(30,24,17,0.06);
    }
    .compact-note {
      color: var(--muted);
      font-size: 13px;
      line-height: 1.55;
    }
    .label {
      display: block;
      margin: 0 0 6px;
      font-size: 12px;
      color: var(--muted);
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }
    input,
    button,
    select,
    textarea {
      width: 100%;
      border-radius: 16px;
      border: 1px solid var(--line);
      background: #fff;
      color: var(--ink);
      font-size: 14px;
      padding: 12px 14px;
      font: inherit;
    }
    textarea { min-height: 96px; resize: vertical; }
    button {
      cursor: pointer;
      border: none;
      background: var(--ink);
      color: #fff;
      font-weight: 700;
    }
    button.secondary {
      background: var(--accent-soft);
      color: var(--ink);
    }
    button.ghost {
      background: #fff;
      border: 1px solid var(--line);
      color: var(--ink);
    }
    .stack-2 {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }
    .stack-3 {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
    }
    .checkbox-row {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      padding: 4px 2px 0;
    }
    .checkbox-row label {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: 13px;
      color: var(--muted);
    }
    .checkbox-row input { width: auto; padding: 0; }
    .mono {
      margin: 0;
      white-space: pre-wrap;
      background: #f5ede0;
      border-radius: 16px;
      padding: 12px;
      font-size: 12px;
      line-height: 1.5;
      color: #50483d;
      max-height: 280px;
      overflow: auto;
    }
    .summary-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
    }
    .summary-card {
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 14px;
      background: rgba(255,255,255,0.75);
    }
    .summary-card strong {
      display: block;
      margin-bottom: 6px;
      font-size: 11px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }
    .summary-card div {
      font-size: 14px;
      line-height: 1.45;
      font-weight: 600;
    }
    .summary-card small,
    .summary-card ul {
      display: block;
      margin: 8px 0 0;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.5;
      padding-left: 18px;
    }
    .question-list {
      display: grid;
      gap: 12px;
      margin-top: 12px;
    }
    .question-card {
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 14px;
      background: rgba(255,255,255,0.74);
    }
    .question-card strong {
      display: block;
      margin-bottom: 8px;
      font-size: 13px;
      line-height: 1.4;
    }
    .main {
      display: grid;
      gap: 18px;
    }
    .decision-actions {
      display: grid;
      gap: 10px;
    }
    .decision-actions button.secondary {
      background: var(--ink);
      color: #fff;
    }
    .canvas-shell {
      display: grid;
      gap: 14px;
    }
    .canvas-stage {
      position: relative;
      min-height: 540px;
      border-radius: 26px;
      border: 1px solid var(--line);
      padding: 28px;
      display: grid;
      overflow: hidden;
    }
    .canvas-stage[data-background="deep-contrast"] { background: linear-gradient(135deg, #18130f, #3c2b18 58%, #0f0d0a); color: #f8f1e6; }
    .canvas-stage[data-background="paper-editorial"] { background: linear-gradient(135deg, #f8f1e4, #efe0c7 60%, #fdfaf5); color: #1d1812; }
    .canvas-stage[data-background="neutral-system"] { background: linear-gradient(135deg, #f5f3ef, #e7e1d8 60%, #ffffff); color: #1d1812; }
    .canvas-stage[data-background="bright-promo"] { background: linear-gradient(135deg, #fff1cf, #ffcf7a 54%, #fff8ea); color: #1d1812; }
    .canvas-stage[data-background="warm-paper"] { background: linear-gradient(135deg, #f7e9d5, #e6bf94 55%, #fdf8ef); color: #1d1812; }
    .canvas-stage[data-background="soft-luxury"] { background: linear-gradient(135deg, #f4eadb, #d9c3a4 55%, #fff8f0); color: #1d1812; }
    .canvas-stage[data-background="tech-grid"] {
      background:
        linear-gradient(transparent 0 96%, rgba(255,255,255,0.10) 96% 100%),
        linear-gradient(90deg, transparent 0 96%, rgba(255,255,255,0.10) 96% 100%),
        linear-gradient(135deg, #111827, #1f3a5f 52%, #0d1320);
      background-size: 28px 28px, 28px 28px, auto;
      color: #eef5ff;
    }
    .canvas-stage[data-layout="left-stack"] { align-content: end; justify-items: start; }
    .canvas-stage[data-layout="split-hero"] { align-content: center; justify-items: start; }
    .canvas-stage[data-layout="center-cover"] { align-content: center; justify-items: center; text-align: center; }
    .canvas-stage[data-layout="banner-stack"] { align-content: center; justify-items: start; }
    .canvas-stage[data-layout="poster-stack"] { align-content: start; justify-items: start; }
    .canvas-copy {
      display: grid;
      gap: 14px;
      max-width: 780px;
    }
    .canvas-stage[data-layout="split-hero"] .canvas-copy { max-width: 56%; }
    .canvas-stage[data-layout="banner-stack"] .canvas-copy { max-width: 62%; }
    .canvas-kicker {
      font-size: 12px;
      letter-spacing: 0.16em;
      text-transform: uppercase;
      opacity: 0.78;
    }
    .canvas-title {
      font-size: clamp(44px, 6vw, 84px);
      line-height: 0.94;
      letter-spacing: -0.05em;
      font-weight: 800;
    }
    .canvas-subtitle {
      font-size: clamp(18px, 2vw, 28px);
      line-height: 1.15;
      font-weight: 650;
      max-width: 34ch;
    }
    .canvas-body {
      font-size: 15px;
      line-height: 1.6;
      max-width: 56ch;
      opacity: 0.86;
    }
    .canvas-role-map {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }
    .role-chip {
      display: inline-flex;
      flex-direction: column;
      gap: 2px;
      border: 1px solid rgba(255,255,255,0.16);
      border-radius: 14px;
      padding: 10px 12px;
      background: rgba(255,255,255,0.08);
      min-width: 140px;
    }
    .canvas-stage[data-background="paper-editorial"] .role-chip,
    .canvas-stage[data-background="neutral-system"] .role-chip,
    .canvas-stage[data-background="bright-promo"] .role-chip,
    .canvas-stage[data-background="warm-paper"] .role-chip,
    .canvas-stage[data-background="soft-luxury"] .role-chip {
      border-color: rgba(0,0,0,0.08);
      background: rgba(255,255,255,0.54);
    }
    .role-chip strong {
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      opacity: 0.74;
    }
    .role-chip span {
      font-size: 13px;
      font-weight: 700;
      line-height: 1.35;
    }
    .canvas-toolbar {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 14px;
    }
    .canvas-toolbar button {
      width: auto;
      min-width: 128px;
    }
    .compare-wrap {
      display: grid;
      gap: 14px;
    }
    .compare-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 14px;
    }
    .compare-card,
    .result-card {
      border: 1px solid var(--line);
      border-radius: 22px;
      overflow: hidden;
      background: var(--panel);
    }
    .compare-card img,
    .result-card img {
      width: 100%;
      display: block;
      aspect-ratio: 1200 / 680;
      background: #faf7ef;
      border-bottom: 1px solid var(--line);
      object-fit: cover;
    }
    .compare-card .body,
    .result-card .body {
      padding: 14px 16px 16px;
    }
    .compare-card strong,
    .result-card h3 {
      margin: 0;
      display: block;
      font-size: 17px;
      line-height: 1.18;
    }
    .result-meta,
    .compare-card span {
      display: block;
      margin-top: 6px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.4;
    }
    .catalog-shell {
      display: grid;
      gap: 14px;
    }
    .catalog-toolbar {
      display: grid;
      grid-template-columns: 1.2fr 120px 150px auto;
      gap: 10px;
      align-items: end;
    }
    .catalog-toggles {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
    }
    .catalog-summary {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
      justify-content: space-between;
    }
    .catalog-count {
      font-size: 13px;
      color: var(--muted);
      line-height: 1.5;
    }
    .catalog-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 16px;
    }
    .catalog-card {
      display: grid;
      grid-template-rows: auto auto;
      border: 1px solid var(--line);
      border-radius: 20px;
      overflow: hidden;
      background: var(--panel);
      min-width: 0;
    }
    .catalog-card img {
      width: 100%;
      display: block;
      aspect-ratio: 1200 / 680;
      background: #faf7ef;
      border-bottom: 1px solid var(--line);
      object-fit: cover;
    }
    .catalog-badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 8px 10px;
      border-radius: 999px;
      font-size: 11px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      font-weight: 700;
      backdrop-filter: blur(8px);
      background: rgba(255,255,255,0.88);
      border: 1px solid rgba(30,24,17,0.10);
    }
    .catalog-card-footer {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      padding: 10px 12px 12px;
      background: rgba(255,253,248,0.96);
    }
    .catalog-badge.license {
      text-transform: none;
      letter-spacing: 0.01em;
      font-size: 12px;
      padding: 8px 12px;
    }
    .catalog-badge.ready {
      color: #0f5132;
      background: rgba(234, 247, 238, 0.94);
    }
    .catalog-badge.assisted {
      color: #8a5312;
      background: rgba(252, 242, 220, 0.94);
    }
    .catalog-badge.manual,
    .catalog-badge.unknown {
      color: #5e4a3a;
      background: rgba(247, 238, 228, 0.94);
    }
    .catalog-badge.blocked {
      color: #7a1f1f;
      background: rgba(252, 228, 228, 0.94);
    }
    .catalog-badge.allowed,
    .license-pill.allowed {
      color: #0f5132;
      background: rgba(234, 247, 238, 0.94);
    }
    .catalog-badge.caution,
    .license-pill.caution {
      color: #8a5312;
      background: rgba(252, 242, 220, 0.94);
    }
    .catalog-badge.unknown,
    .license-pill.unknown {
      color: #5e4a3a;
      background: rgba(247, 238, 228, 0.94);
    }
    .catalog-badge.blocked.license,
    .license-pill.blocked {
      color: #7a1f1f;
      background: rgba(252, 228, 228, 0.94);
    }
    .license-pill {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      margin-top: 10px;
      padding: 7px 11px;
      border-radius: 999px;
      border: 1px solid rgba(30,24,17,0.10);
      font-size: 12px;
      font-weight: 700;
      line-height: 1;
    }
    .license-detail {
      display: block;
      margin-top: 8px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.45;
    }
    .catalog-pagination {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }
    .catalog-pagination button {
      width: auto;
      min-width: 42px;
      padding: 10px 12px;
      background: #fff;
      border: 1px solid var(--line);
      color: var(--ink);
    }
    .catalog-pagination button.active {
      background: var(--ink);
      color: #fff;
      border-color: var(--ink);
    }
    .rail.left .results {
      grid-template-columns: 1fr;
    }
    .tag-list {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 12px;
    }
    .tag {
      display: inline-flex;
      align-items: center;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 6px 10px;
      font-size: 12px;
      color: var(--muted);
      background: #fff;
    }
    .card-actions {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
      margin-top: 12px;
    }
    .bundle-links,
    .artifact-links {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 12px;
    }
    .bundle-links a,
    .artifact-links a {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 10px 12px;
      border-radius: 12px;
      text-decoration: none;
      background: var(--accent-soft);
      color: var(--ink);
      font-size: 13px;
      border: 1px solid var(--line);
    }
    .drawer-backdrop {
      position: fixed;
      inset: 0;
      background: rgba(19, 16, 12, 0.46);
      opacity: 0;
      pointer-events: none;
      transition: opacity 180ms ease;
      z-index: 50;
    }
    .drawer {
      position: fixed;
      top: 0;
      right: 0;
      width: min(480px, 92vw);
      height: 100vh;
      background: var(--panel);
      border-left: 1px solid var(--line);
      box-shadow: -12px 0 40px rgba(30,24,17,0.12);
      transform: translateX(102%);
      transition: transform 220ms ease;
      z-index: 60;
      display: grid;
      grid-template-rows: auto auto 1fr;
    }
    .drawer.open { transform: translateX(0); }
    .drawer-backdrop.open {
      opacity: 1;
      pointer-events: auto;
    }
    .drawer-head {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      padding: 18px 20px 12px;
      border-bottom: 1px solid var(--line);
    }
    .drawer-head h3 {
      margin: 0;
      font-size: 20px;
    }
    .drawer-tabs {
      display: flex;
      gap: 8px;
      padding: 14px 20px 0;
      flex-wrap: wrap;
    }
    .drawer-tabs button {
      width: auto;
      background: #fff;
      border: 1px solid var(--line);
      color: var(--muted);
      padding: 10px 12px;
    }
    .drawer-tabs button.active {
      background: var(--ink);
      color: #fff;
      border-color: var(--ink);
    }
    .drawer-body {
      overflow: auto;
      padding: 16px 20px 24px;
    }
    .drawer-panel { display: none; }
    .drawer-panel.active { display: block; }
    .role-list {
      display: grid;
      gap: 10px;
    }
    .role-card {
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 14px;
      background: rgba(255,255,255,0.72);
    }
    .role-card strong {
      display: block;
      margin-bottom: 6px;
      font-size: 12px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }
    .role-card h4 {
      margin: 0;
      font-size: 16px;
      line-height: 1.18;
    }
    .role-card p {
      margin-top: 8px;
      font-size: 13px;
      color: var(--muted);
    }
    .hint-group {
      display: grid;
      gap: 10px;
    }
    .hint-card {
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 14px;
      background: rgba(255,255,255,0.72);
    }
    .hint-card strong {
      display: block;
      margin-bottom: 8px;
      font-size: 11px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }
    .hint-card ul {
      margin: 8px 0 0;
      padding-left: 18px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.5;
    }
    .empty {
      color: var(--muted);
      font-size: 14px;
      line-height: 1.55;
    }
    details {
      border-top: 1px solid var(--line);
      margin-top: 14px;
      padding-top: 14px;
    }
    summary {
      cursor: pointer;
      font-size: 13px;
      color: var(--muted);
      font-weight: 700;
    }
    @media (max-width: 1320px) {
      .workspace { grid-template-columns: 300px minmax(0, 1fr); }
    }
    @media (max-width: 980px) {
      .hero,
      .workspace { grid-template-columns: 1fr; }
      .rail { position: static; }
      .stack-2,
      .stack-3 { grid-template-columns: 1fr; }
      .workflow-strip,
      .quick-preset-grid,
      .catalog-toolbar { grid-template-columns: 1fr; }
      .catalog-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }
    @media (max-width: 720px) {
      .catalog-grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="page">
    <section class="hero">
      <article class="panel hero-copy">
        <div class="eyebrow">Typography Decision Board</div>
        <h1>FontAgent</h1>
        <p>후보 폰트를 비교하고, 역할별 조합을 정한 뒤, 프로젝트용 font system과 typography handoff로 내보내는 대시보드입니다.</p>
        <div class="workflow-strip">
          <div class="workflow-card">
            <strong>1. Choose A Starting Point</strong>
            <span>빠른 시작 프리셋으로 현재 결정하려는 타이포 상황을 먼저 고릅니다.</span>
          </div>
          <div class="workflow-card">
            <strong>2. Compare Candidates</strong>
            <span>같은 문구를 나란히 보면서 어떤 가족이 역할에 맞는지 빠르게 걸러냅니다.</span>
          </div>
          <div class="workflow-card">
            <strong>3. Export The System</strong>
            <span>결정이 끝나면 font system, template bundle, handoff를 생성해 다음 에이전트로 넘깁니다.</span>
          </div>
        </div>
      </article>
    </section>

    <section class="workspace">
      <aside class="rail left">
        <section class="panel">
          <div class="section-title">
            <h3>Quick Start</h3>
            <span>Choose What To Decide</span>
          </div>
          <div class="controls">
            <div id="quickPresetGrid" class="quick-preset-grid"></div>
            <div id="presetSummary" class="summary-card">
              <strong>Active Preset</strong>
              <div>첫 시작 프리셋을 고르면 이 영역이 현재 타이포 결정 질문을 설명합니다.</div>
            </div>
            <div class="stack-2">
              <div>
                <label class="label" for="useCase">Use Case</label>
                <select id="useCase"></select>
              </div>
              <div>
                <label class="label" for="language">Language</label>
                <input id="language" value="ko" placeholder="ko / en" />
              </div>
            </div>
            <div>
              <label class="label" for="task">Task Brief</label>
              <textarea id="task">youtube video thumbnail title cinematic display korean</textarea>
            </div>
            <div>
              <label class="label" for="sampleText">Compare Sample</label>
              <input id="sampleText" value="역사는 왜 반복처럼 보일까" placeholder="비교 미리보기 문구" />
            </div>
            <div class="checkbox-row">
              <label><input id="commercialUse" type="checkbox" checked /> 상업 사용</label>
              <label><input id="videoUse" type="checkbox" checked /> 영상 사용</label>
              <label><input id="webEmbedding" type="checkbox" /> 웹 임베딩</label>
            </div>
            <div class="stack-2">
              <button onclick="runUseCaseRecommend()">추천 갱신</button>
              <button class="secondary" onclick="runRecommend()">task 추천</button>
            </div>
            <button class="ghost" onclick="runSearch()">자유 검색</button>
            <p class="compact-note">핵심은 후보 비교입니다. 검색은 보조 수단이고, 현재 프리셋에 맞는 role/medium/surface는 아래 Advanced에서 수정할 수 있습니다.</p>
          </div>
        </section>

        <section class="panel">
          <div class="section-title">
            <h3>Commit / Export</h3>
            <span>Project Outputs</span>
          </div>
          <div class="decision-actions">
            <button class="secondary" onclick="prepareFontSystem()">폰트 시스템 생성</button>
            <button onclick="generateTemplateBundle()">템플릿 번들 생성</button>
            <button class="ghost" onclick="generateTypographyHandoff()">Typography Handoff 생성</button>
            <p class="compact-note">비교가 끝난 뒤에는 이 패널에서 프로젝트용 산출물을 만들고, drawer에서 결과 경로를 확인합니다.</p>
          </div>
        </section>

        <section class="panel">
          <div class="section-title">
            <h3>Advanced Controls</h3>
            <span>Optional</span>
          </div>
          <div class="controls">
            <details>
              <summary>검색 / 구조화 입력</summary>
              <div class="controls" style="margin-top:12px;">
                <div>
                  <label class="label" for="query">Search Query</label>
                  <input id="query" value="documentary title" placeholder="예: documentary subtitle serif" />
                </div>
                <div class="stack-3">
                  <div>
                    <label class="label" for="medium">Medium</label>
                    <input id="medium" value="video" placeholder="video / web / print" />
                  </div>
                  <div>
                    <label class="label" for="surface">Surface</label>
                    <input id="surface" value="thumbnail" placeholder="thumbnail / landing_hero" />
                  </div>
                  <div>
                    <label class="label" for="role">Primary Role</label>
                    <input id="role" value="title" placeholder="title / subtitle / body" />
                  </div>
                </div>
                <div>
                  <label class="label" for="tones">Tones</label>
                  <input id="tones" value="cinematic, display" placeholder="cinematic, retro, editorial" />
                </div>
              </div>
            </details>
            <details>
              <summary>가이드 인터뷰</summary>
              <div class="controls" style="margin-top:12px;">
                <div class="stack-2">
                  <div>
                    <label class="label" for="interviewCategory">Category</label>
                    <select id="interviewCategory"></select>
                  </div>
                  <div>
                    <label class="label" for="interviewSubcategory">Subcategory</label>
                    <select id="interviewSubcategory"></select>
                  </div>
                </div>
                <div id="interviewQuestions" class="question-list"></div>
                <button onclick="runInterviewRecommend()">인터뷰 기반 추천</button>
                <p class="compact-note">인터뷰는 방향이 모호할 때만 쓰는 보조 모드입니다. 메인 워크플로는 위의 프리셋과 후보 비교입니다.</p>
              </div>
            </details>
            <details>
              <summary>출력 경로 / 설치 액션</summary>
              <div class="controls" style="margin-top:12px;">
                <div>
                  <label class="label" for="projectPath">Project Path</label>
                  <input id="projectPath" value="./demo-project" placeholder="프로젝트 경로" />
                </div>
                <div class="stack-2">
                  <div>
                    <label class="label" for="installDir">Install Dir</label>
                    <input id="installDir" value="./installed_fonts" placeholder="설치 경로" />
                  </div>
                  <div>
                    <label class="label" for="browserTaskDir">Browser Task Dir</label>
                    <input id="browserTaskDir" value="./examples/browser_tasks" placeholder="브라우저 작업 경로" />
                  </div>
                </div>
              </div>
            </details>
          </div>
        </section>
      </aside>

      <main class="main">
        <section class="panel">
          <div class="section-title">
            <h2>Current Decision</h2>
            <span>Request Brief</span>
          </div>
          <div id="requestSummary" class="empty">검색이나 추천을 실행하면 현재 medium, surface, role, tone, 라이선스 조건이 이 영역에 정리됩니다.</div>
        </section>

        <section class="panel">
          <div class="section-title">
            <h2>Compare Candidates</h2>
            <span>Preview / Actions</span>
          </div>
          <div id="compare" class="compare-wrap empty">상위 후보를 같은 문구로 나란히 보여줍니다.</div>
          <div style="margin-top:18px;">
            <div class="section-title" style="margin-bottom:12px;">
              <h3>Applicable Font Catalog</h3>
              <span>Noonnu-Style Gallery</span>
            </div>
            <div class="catalog-shell">
              <div class="catalog-toolbar">
                <div>
                  <label class="label" for="catalogQuery">Catalog Search</label>
                  <input id="catalogQuery" value="" placeholder="폰트 이름, 태그, 출처 검색" />
                </div>
                <div>
                  <label class="label" for="catalogLanguage">Language</label>
                  <select id="catalogLanguage">
                    <option value="">all</option>
                    <option value="ko" selected>ko</option>
                    <option value="en">en</option>
                  </select>
                </div>
                <div>
                  <label class="label" for="catalogPreset">Specimen</label>
                  <select id="catalogPreset">
                    <option value="title-ko">Title / Korean</option>
                    <option value="subtitle-ko">Subtitle / Korean</option>
                    <option value="body-ko">Body / Korean</option>
                    <option value="title-en">Title / English</option>
                    <option value="subtitle-en">Subtitle / English</option>
                    <option value="body-en">Body / English</option>
                  </select>
                </div>
                <button onclick="refreshCatalog()">갤러리 새로고침</button>
              </div>
              <div class="catalog-summary">
                <div class="catalog-toggles checkbox-row">
                  <label><input id="catalogCommercialOnly" type="checkbox" checked /> 상업 사용</label>
                  <label><input id="catalogVideoOnly" type="checkbox" /> 영상 사용</label>
                  <label><input id="catalogWebOnly" type="checkbox" /> 웹 임베딩</label>
                </div>
                <div id="catalogCount" class="catalog-count">현재 조건에 맞는 전체 카탈로그를 불러오면 수량이 여기 표시됩니다.</div>
              </div>
              <div id="catalogGallery" class="catalog-grid"></div>
              <div id="catalogPagination" class="catalog-pagination"></div>
            </div>
          </div>
        </section>

        <section class="panel">
          <div class="section-title">
            <h2>Typography Skeleton</h2>
            <span>Optional Guided Preview</span>
          </div>
          <div id="interviewCanvas" class="empty">인터뷰 기반 추천을 실행하면 기본 레이아웃과 role별 폰트 시스템이 여기에 배치됩니다.</div>
        </section>
      </main>
    </section>
  </div>

  <div id="drawerBackdrop" class="drawer-backdrop" onclick="closeDrawer()"></div>
  <aside id="detailDrawer" class="drawer" aria-hidden="true">
    <div class="drawer-head">
      <h3>상세 패널</h3>
      <button class="ghost" onclick="closeDrawer()">닫기</button>
    </div>
    <div class="drawer-tabs">
      <button id="drawer-tab-system" onclick="openDrawer('system')">폰트 시스템</button>
      <button id="drawer-tab-template" onclick="openDrawer('template')">템플릿</button>
      <button id="drawer-tab-handoff" onclick="openDrawer('handoff')">handoff</button>
    </div>
    <div class="drawer-body">
      <section id="drawer-panel-system" class="drawer-panel">
        <div id="systemSummary" class="empty">프로젝트 폰트 시스템을 만들면 title, subtitle, body 역할과 export 경로가 여기에 정리됩니다.</div>
        <details>
          <summary>raw output</summary>
          <pre id="systemOut" class="mono">font system output</pre>
        </details>
      </section>
      <section id="drawer-panel-template" class="drawer-panel">
        <div id="templateOut" class="empty">템플릿 번들을 생성하면 HTML/CSS 아티팩트 링크가 여기에 나타납니다.</div>
      </section>
      <section id="drawer-panel-handoff" class="drawer-panel">
        <div id="handoffSummary" class="empty">디자인 에이전트와 협업할 때 넘길 typography contract가 여기에 정리됩니다.</div>
        <details>
          <summary>raw output</summary>
          <pre id="handoffOut" class="mono">typography handoff output</pre>
        </details>
      </section>
    </div>
  </aside>

  <script>
    const state = {
      results: [],
      previews: [],
      request: null,
      system: null,
      handoff: null,
      interviewCatalog: {},
      interviewData: null,
      useCases: {},
      activePreset: '',
      catalogCount: 0,
      catalogPage: 1,
      catalogTotalPages: 1,
    };

    const QUICK_PRESETS = {
      'youtube-thumbnail-ko': {
        label: '썸네일 제목',
        description: '짧고 강한 display 제목 후보를 빠르게 비교합니다.',
        use_case: 'youtube-thumbnail-ko',
        task: 'youtube video thumbnail title cinematic display korean',
        query: 'cinematic korean thumbnail title',
        medium: 'video',
        surface: 'thumbnail',
        role: 'title',
        tones: ['cinematic', 'display'],
        language: 'ko',
        sample_text: '지금 이 변화가 시장을 바꾼다',
      },
      'documentary-landing-ko': {
        label: '랜딩 헤드라인',
        description: '다큐/에디토리얼 무드의 hero headline 조합을 고릅니다.',
        use_case: 'documentary-landing-ko',
        task: 'documentary landing hero editorial title korean',
        query: 'documentary landing editorial title',
        medium: 'web',
        surface: 'landing_hero',
        role: 'title',
        tones: ['editorial', 'documentary'],
        language: 'ko',
        sample_text: '한 시대의 균열은 문장보다 먼저 제목에서 드러난다',
      },
      'poster-headline': {
        label: '포스터 헤드라인',
        description: '굵고 존재감 큰 headline 가족을 poster 기준으로 비교합니다.',
        use_case: 'poster-headline',
        task: 'print poster headline display',
        query: 'poster display headline',
        medium: 'print',
        surface: 'poster_headline',
        role: 'title',
        tones: ['poster', 'display'],
        language: 'ko',
        sample_text: '도시는 한 장의 포스터처럼 기억된다',
      },
      'presentation-cover': {
        label: '슬라이드 커버',
        description: 'deck 첫 장에 맞는 clean display 계열을 추립니다.',
        use_case: 'presentation-cover',
        task: 'presentation cover title display',
        query: 'presentation cover title display',
        medium: 'presentation',
        surface: 'cover',
        role: 'title',
        tones: ['brand'],
        language: 'ko',
        sample_text: '2026 Strategic Narrative',
      },
      'video-subtitle': {
        label: '영상 자막',
        description: '읽기 속도와 안정성이 중요한 subtitle 후보를 비교합니다.',
        use_case: 'video-subtitle',
        task: 'video subtitle readable sans',
        query: 'subtitle readable sans',
        medium: 'video',
        surface: 'subtitle_track',
        role: 'subtitle',
        tones: ['readable'],
        language: 'ko',
        sample_text: '가독성은 자막에서 가장 먼저 검증됩니다.',
      },
      'document-body': {
        label: '문서 본문',
        description: '긴 문단과 설명 블록에 버티는 readable body 계열을 고릅니다.',
        use_case: 'document-body',
        task: 'document body editorial readable',
        query: 'document body editorial readable',
        medium: 'document',
        surface: 'body_copy',
        role: 'body',
        tones: ['editorial'],
        language: 'ko',
        sample_text: '본문은 오래 읽혀도 피로하지 않아야 합니다.',
      },
    };

    async function postJson(url, payload) {
      const response = await fetch(url, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload),
      });
      return await response.json();
    }

    function esc(value) {
      return String(value ?? '').replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
    }

    function artifactUrl(path) {
      if (!path) {
        return '';
      }
      return `/artifacts?path=${encodeURIComponent(path)}`;
    }

    function useCaseLabel(name) {
      if (!name) {
        return 'custom';
      }
      return (QUICK_PRESETS[name] || {}).label || name;
    }

    function suggestedCatalogPreset(role, language) {
      let base = 'title';
      if (role === 'subtitle' || role === 'caption') {
        base = 'subtitle';
      } else if (role === 'body') {
        base = 'body';
      }
      const suffix = language === 'en' ? 'en' : 'ko';
      return `${base}-${suffix}`;
    }

    function renderQuickPresets() {
      const container = document.getElementById('quickPresetGrid');
      container.innerHTML = Object.entries(QUICK_PRESETS).map(([key, preset]) => `
        <button class="preset-chip ${state.activePreset === key ? 'active' : ''}" onclick="applyQuickPreset('${esc(key)}')">
          <strong>${esc(preset.label)}</strong>
          <span>${esc(preset.description)}</span>
        </button>
      `).join('');
    }

    function renderPresetSummary(name) {
      const preset = QUICK_PRESETS[name];
      const container = document.getElementById('presetSummary');
      if (!preset) {
        container.innerHTML = `
          <strong>Active Preset</strong>
          <div>커스텀 입력 모드</div>
          <small>현재는 직접 medium, surface, role, task를 조합해서 비교하는 상태입니다.</small>
        `;
        return;
      }
      container.innerHTML = `
        <strong>Active Preset</strong>
        <div>${esc(preset.label)} · ${esc(preset.medium)} / ${esc(preset.surface)} / ${esc(preset.role)}</div>
        <small>${esc(preset.description)} ${esc((preset.tones || []).join(', '))}</small>
      `;
    }

    function applyQuickPreset(name, options = {}) {
      const preset = QUICK_PRESETS[name];
      if (!preset) {
        return;
      }
      state.activePreset = name;
      document.getElementById('useCase').value = preset.use_case || '';
      document.getElementById('language').value = preset.language || 'ko';
      document.getElementById('task').value = preset.task || '';
      document.getElementById('query').value = preset.query || '';
      document.getElementById('medium').value = preset.medium || '';
      document.getElementById('surface').value = preset.surface || '';
      document.getElementById('role').value = preset.role || '';
      document.getElementById('tones').value = (preset.tones || []).join(', ');
      document.getElementById('sampleText').value = preset.sample_text || '';
      document.getElementById('catalogLanguage').value = preset.language || 'ko';
      document.getElementById('catalogPreset').value = suggestedCatalogPreset(preset.role, preset.language);
      renderQuickPresets();
      renderPresetSummary(name);
      if (options.run !== false) {
        runUseCaseRecommend();
      }
    }

    function openDrawer(panel) {
      const drawer = document.getElementById('detailDrawer');
      const backdrop = document.getElementById('drawerBackdrop');
      drawer.classList.add('open');
      drawer.setAttribute('aria-hidden', 'false');
      backdrop.classList.add('open');
      ['system', 'template', 'handoff'].forEach((name) => {
        document.getElementById(`drawer-panel-${name}`).classList.toggle('active', name === panel);
        document.getElementById(`drawer-tab-${name}`).classList.toggle('active', name === panel);
      });
    }

    function closeDrawer() {
      document.getElementById('detailDrawer').classList.remove('open');
      document.getElementById('detailDrawer').setAttribute('aria-hidden', 'true');
      document.getElementById('drawerBackdrop').classList.remove('open');
    }

    function renderTagList(items) {
      const safeItems = (items || []).filter(Boolean);
      if (!safeItems.length) {
        return '<span class="tag">tag 없음</span>';
      }
      return safeItems.map((item) => `<span class="tag">${esc(item)}</span>`).join('');
    }

    function renderLines(items) {
      const safeItems = (items || []).filter(Boolean);
      if (!safeItems.length) {
        return '<span class="empty">설명 없음</span>';
      }
      return `<ul>${safeItems.map((item) => `<li>${esc(item)}</li>`).join('')}</ul>`;
    }

    function setMono(id, data) {
      document.getElementById(id).textContent = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
    }

    function setOptionalMono(id, data) {
      const element = document.getElementById(id);
      if (!element) {
        return;
      }
      element.textContent = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
    }

    function previewAssetUrl(fontId, preset, sampleText) {
      const params = new URLSearchParams({
        font_id: fontId,
        preset: preset || 'title-ko',
      });
      if (sampleText) {
        params.set('sample_text', sampleText);
      }
      return `/fonts/preview.svg?${params.toString()}`;
    }

    function currentRequest() {
      return {
        query: document.getElementById('query').value,
        task: document.getElementById('task').value,
        language: document.getElementById('language').value,
        use_case: document.getElementById('useCase').value,
        medium: document.getElementById('medium').value,
        surface: document.getElementById('surface').value,
        role: document.getElementById('role').value,
        tones: document.getElementById('tones').value.split(',').map((value) => value.trim()).filter(Boolean),
        constraints: {
          commercial_use: document.getElementById('commercialUse').checked,
          video_use: document.getElementById('videoUse').checked,
          web_embedding: document.getElementById('webEmbedding').checked,
        },
      };
    }

    async function loadUseCases() {
      const response = await fetch('/fonts/use-cases');
      const data = await response.json();
      state.useCases = data.use_cases || {};
      const select = document.getElementById('useCase');
      const options = ['<option value="">직접 입력</option>'].concat(
        Object.keys(state.useCases).map((name) => `<option value="${esc(name)}">${esc(useCaseLabel(name))}</option>`)
      );
      select.innerHTML = options.join('');
    }

    async function loadInterviewCatalog() {
      const response = await fetch('/fonts/interview-catalog');
      const data = await response.json();
      state.interviewCatalog = data.categories || {};
      const categorySelect = document.getElementById('interviewCategory');
      const categoryEntries = Object.entries(state.interviewCatalog);
      categorySelect.innerHTML = categoryEntries.map(([key, value]) => `<option value="${esc(key)}">${esc(value.label)}</option>`).join('');
      if (categoryEntries.length) {
        categorySelect.value = categoryEntries[0][0];
      }
      updateInterviewSubcategories();
    }

    function updateInterviewSubcategories() {
      const category = document.getElementById('interviewCategory').value;
      const subcategorySelect = document.getElementById('interviewSubcategory');
      const categoryInfo = state.interviewCatalog[category] || { subcategories: {} };
      const subcategoryEntries = Object.entries(categoryInfo.subcategories || {});
      subcategorySelect.innerHTML = subcategoryEntries.map(([key, value]) => `<option value="${esc(key)}">${esc(value.label)}</option>`).join('');
      if (subcategoryEntries.length) {
        subcategorySelect.value = subcategoryEntries[0][0];
      }
      renderInterviewQuestions();
    }

    function renderInterviewQuestions() {
      const category = document.getElementById('interviewCategory').value;
      const subcategory = document.getElementById('interviewSubcategory').value;
      const flow = (((state.interviewCatalog || {})[category] || {}).subcategories || {})[subcategory];
      const container = document.getElementById('interviewQuestions');
      if (!flow) {
        container.innerHTML = '<div class="empty">선택 가능한 인터뷰가 없습니다.</div>';
        return;
      }
      container.innerHTML = (flow.questions || []).map((question) => `
        <article class="question-card">
          <strong>${esc(question.label)}</strong>
          <select id="question-${esc(question.id)}">
            ${(question.options || []).map((option) => `
              <option value="${esc(option.value)}" ${option.value === question.default ? 'selected' : ''}>${esc(option.label)}</option>
            `).join('')}
          </select>
        </article>
      `).join('');
    }

    function collectInterviewAnswers() {
      const category = document.getElementById('interviewCategory').value;
      const subcategory = document.getElementById('interviewSubcategory').value;
      const flow = (((state.interviewCatalog || {})[category] || {}).subcategories || {})[subcategory];
      const answers = {};
      for (const question of (flow?.questions || [])) {
        const field = document.getElementById(`question-${question.id}`);
        if (field) {
          answers[question.id] = field.value;
        }
      }
      return answers;
    }

    function syncRequestFields(request) {
      if (!request) {
        return;
      }
      if (request.use_case !== undefined) {
        document.getElementById('useCase').value = request.use_case || '';
      }
      document.getElementById('medium').value = request.medium || '';
      document.getElementById('surface').value = request.surface || '';
      document.getElementById('role').value = request.role || '';
      document.getElementById('tones').value = (request.tones || []).join(', ');
      document.getElementById('language').value = ((request.languages || [request.language]).filter(Boolean)[0]) || '';
      const constraints = request.constraints || {};
      document.getElementById('commercialUse').checked = Boolean(constraints.commercial_use);
      document.getElementById('videoUse').checked = Boolean(constraints.video_use);
      document.getElementById('webEmbedding').checked = Boolean(constraints.web_embedding);
    }

    function renderRequestSummary(request) {
      const container = document.getElementById('requestSummary');
      if (!request) {
        container.innerHTML = '<div class="empty">현재 요청 정보가 없습니다.</div>';
        return;
      }
      const tones = request.tones || [];
      const primaryLanguage = request.language || ((request.languages || []).find(Boolean)) || 'n/a';
      const constraints = request.constraints || {};
      const useCase = request.use_case || state.activePreset || '';
      container.innerHTML = `
        <div class="summary-grid">
          <div class="summary-card">
            <strong>Decision Context</strong>
            <div>${esc(request.medium || 'n/a')} / ${esc(request.surface || 'n/a')} / ${esc(request.role || 'n/a')}</div>
            <small>${esc(request.task || request.query || '')}</small>
          </div>
          <div class="summary-card">
            <strong>Language & Starting Point</strong>
            <div>${esc(primaryLanguage)} · ${esc(useCaseLabel(useCase))}</div>
            <small>${tones.length ? esc(tones.join(', ')) : 'tone 미지정'}</small>
          </div>
          <div class="summary-card">
            <strong>License Constraints</strong>
            <div>${Object.entries(constraints).map(([key, value]) => `${key}=${value ? 'yes' : 'no'}`).join(' · ')}</div>
            <small>추천 결과는 이 조건을 중심으로 필터링됩니다.</small>
          </div>
        </div>
      `;
    }

    function renderInterviewCanvas(data) {
      const container = document.getElementById('interviewCanvas');
      if (!data || !data.canvas) {
        container.innerHTML = '<div class="empty">인터뷰 기반 추천을 실행하면 기본 타이포 레이아웃과 role별 draft font system이 여기에 나타납니다.</div>';
        return;
      }
      const canvas = data.canvas || {};
      const copy = data.recommended_copy || {};
      const roles = ((data.font_system_preview || {}).roles || {});
      const roleMap = Object.entries(roles).map(([name, role]) => `
        <div class="role-chip">
          <strong>${esc(name)}</strong>
          <span>${esc(role.family)}</span>
        </div>
      `).join('');
      const interviewSummary = (data.interview_summary || []).map((item) => `${item.label}: ${item.answer_label}`);
      container.innerHTML = `
        <div class="canvas-shell">
          <div class="summary-grid">
            <div class="summary-card">
              <strong>Category</strong>
              <div>${esc(data.category_label || data.category || '')} / ${esc(data.subcategory_label || data.subcategory || '')}</div>
              <small>${esc(data.query || '')}</small>
            </div>
            <div class="summary-card">
              <strong>Interview Summary</strong>
              ${renderLines(interviewSummary)}
            </div>
            <div class="summary-card">
              <strong>Canvas Notes</strong>
              ${renderLines(canvas.notes || [])}
            </div>
          </div>
          <div class="canvas-stage" data-layout="${esc(canvas.layout_mode || 'left-stack')}" data-background="${esc(canvas.background_mode || 'paper-editorial')}">
            <div class="canvas-copy">
              <div class="canvas-kicker">${esc(copy.kicker || '')}</div>
              <div class="canvas-title">${esc(copy.title || '')}</div>
              <div class="canvas-subtitle">${esc(copy.subtitle || '')}</div>
              <div class="canvas-body">${esc(copy.body || '')}</div>
              <div class="canvas-role-map">${roleMap}</div>
            </div>
          </div>
          <div class="summary-grid">
            <div class="summary-card">
              <strong>Draft Font System</strong>
              <div>${Object.values(roles).map((role) => role.family).join(' / ')}</div>
              <small>실제 glyph 비교는 아래 후보 카드에서 계속 진행합니다.</small>
            </div>
            <div class="summary-card">
              <strong>Ratio Hint</strong>
              <div>${esc(canvas.ratio_hint || 'n/a')}</div>
              <small>이 레이아웃은 완성 디자인이 아니라 typography skeleton입니다.</small>
            </div>
          </div>
        </div>
      `;
    }

    async function enrichPreview(fontId, preset) {
      const sampleText = document.getElementById('sampleText').value;
      const result = await postJson('/fonts/preview', {
        font_id: fontId,
        preset: preset || 'title-ko',
        sample_text: sampleText,
      });
      return result.preview_url || '';
    }

    function renderCompare(results, previewUrls) {
      const container = document.getElementById('compare');
      if (!results.length) {
        container.innerHTML = '<div class="empty">비교할 후보가 없습니다.</div>';
        return;
      }
      const cards = results.slice(0, 4).map((font, index) => `
        <article class="compare-card">
          <img src="${previewUrls[index] || ''}" alt="${esc(font.family)} compare preview" />
          <div class="body">
            <strong>${esc(font.family)}</strong>
            <span>${esc(font.source_site || '')}</span>
            <div class="license-pill ${esc(licenseProfileStatus(font.license_profile || {}))}">${esc(licenseBadgeLabel(font.license_profile || {}))}</div>
            <span class="license-detail">${esc(licenseBadgeDetail(font.license_profile || {}))}</span>
            ${renderLines((font.why || []).slice(0, 2))}
          </div>
        </article>
      `).join('');
      container.innerHTML = `<div class="compare-grid">${cards}</div>`;
    }

    function renderCatalogPagination(page, totalPages) {
      const container = document.getElementById('catalogPagination');
      if (!totalPages || totalPages <= 1) {
        container.innerHTML = '';
        return;
      }
      const start = Math.max(1, page - 4);
      const end = Math.min(totalPages, start + 8);
      const buttons = [];
      if (page > 1) {
        buttons.push(`<button onclick="refreshCatalog(${page - 1})">이전</button>`);
      }
      for (let number = start; number <= end; number += 1) {
        buttons.push(`<button class="${number === page ? 'active' : ''}" onclick="refreshCatalog(${number})">${number}</button>`);
      }
      if (page < totalPages) {
        buttons.push(`<button onclick="refreshCatalog(${page + 1})">다음</button>`);
      }
      container.innerHTML = buttons.join('');
    }

    function catalogBadgeLabel(status) {
      const normalized = (status || 'unknown').toLowerCase();
      const labels = {
        ready: 'AUTO READY',
        assisted: 'AUTO ASSIST',
        manual: 'AUTO MANUAL',
        blocked: 'AUTO BLOCKED',
        unknown: 'AUTO CHECK',
      };
      return labels[normalized] || labels.unknown;
    }

    function licenseProfileStatus(profile = {}) {
      const normalized = String(profile.status || 'unknown').toLowerCase();
      if (normalized === 'allowed') {
        return 'allowed';
      }
      if (normalized === 'caution') {
        return 'caution';
      }
      if (normalized === 'blocked') {
        return 'blocked';
      }
      return 'unknown';
    }

    function licenseBadgeLabel(profile = {}) {
      const status = licenseProfileStatus(profile);
      if (status === 'allowed') {
        return '상업 가능';
      }
      if (status === 'caution') {
        return '상업 가능 · 확인';
      }
      if (status === 'blocked') {
        return '상업 제한';
      }
      return '확인 필요';
    }

    function licenseBadgeDetail(profile = {}) {
      const status = licenseProfileStatus(profile);
      if (status === 'allowed') {
        return '상업 사용 가능이 확인된 폰트입니다.';
      }
      if (status === 'caution') {
        return '상업 사용은 가능하지만 매체 범위나 원문 확인이 더 필요합니다.';
      }
      if (status === 'blocked') {
        return '상업 사용 제한 문구가 확인됐습니다.';
      }
      return '상업 사용 가능 여부가 구조화되지 않았습니다.';
    }

    function renderCatalog(results, meta = {}) {
      const container = document.getElementById('catalogGallery');
      const count = document.getElementById('catalogCount');
      if (!results.length) {
        count.textContent = '현재 카탈로그 조건에 맞는 폰트가 없습니다.';
        container.innerHTML = '<div class="empty">조건을 조정해서 다시 불러와 보세요.</div>';
        renderCatalogPagination(1, 1);
        return;
      }
      const preset = document.getElementById('catalogPreset').value || 'title-ko';
      const sampleText = document.getElementById('sampleText').value;
      const page = meta.page || 1;
      const totalPages = meta.total_pages || 1;
      const totalCount = meta.count || results.length;
      count.textContent = `${totalCount}개 폰트 중 ${page} / ${totalPages} 페이지입니다. 한 번에 20개씩 보여줍니다.`;
      container.innerHTML = results.map((font) => {
        const previewUrl = previewAssetUrl(font.font_id, preset, sampleText);
        const automationProfile = font.automation_profile || {};
        const licenseProfile = font.license_profile || {};
        const badgeStatus = automationProfile.status || 'unknown';
        return `
          <article class="catalog-card">
            <img loading="lazy" src="${previewUrl}" alt="${esc(font.family)} catalog preview" />
            <div class="catalog-card-footer">
              <div class="catalog-badge license ${esc(licenseProfileStatus(licenseProfile))}">${esc(licenseBadgeLabel(licenseProfile))}</div>
              <div class="catalog-badge ${esc(badgeStatus)}">${esc(catalogBadgeLabel(badgeStatus))}</div>
            </div>
          </article>
        `;
      }).join('');
      renderCatalogPagination(page, totalPages);
    }

    async function refreshCatalog(page = 1) {
      const query = document.getElementById('catalogQuery').value;
      const language = document.getElementById('catalogLanguage').value;
      const commercialOnly = document.getElementById('catalogCommercialOnly').checked;
      const videoOnly = document.getElementById('catalogVideoOnly').checked;
      const webOnly = document.getElementById('catalogWebOnly').checked;
      const params = new URLSearchParams({
        query,
        language,
        commercial_only: String(commercialOnly),
        video_only: String(videoOnly),
        web_embedding_only: String(webOnly),
        detail: 'compact',
        page: String(page),
        page_size: '20',
      });
      const response = await fetch(`/fonts/catalog?${params.toString()}`);
      const data = await response.json();
      state.catalogCount = data.count || 0;
      state.catalogPage = data.page || 1;
      state.catalogTotalPages = data.total_pages || 1;
      renderCatalog(data.results || [], data);
    }

    function renderSystemSummary(data) {
      const container = document.getElementById('systemSummary');
      if (!data || !data.roles) {
        container.innerHTML = '<div class="empty">아직 생성된 폰트 시스템이 없습니다.</div>';
        return;
      }
      const roles = Object.entries(data.roles || {}).map(([name, role]) => `
        <article class="role-card">
          <strong>${esc(name)}</strong>
          <h4>${esc(role.family)}</h4>
          <p>${esc(role.generic_family || '')} · ${esc(role.source_site || '')}</p>
          <div class="license-pill ${esc(licenseProfileStatus(role.license_profile || {}))}">${esc(licenseBadgeLabel(role.license_profile || {}))}</div>
          <span class="license-detail">${esc(role.license_summary || licenseBadgeDetail(role.license_profile || {}))}</span>
          <div class="tag-list">${renderTagList(role.tags || [])}</div>
        </article>
      `).join('');
      const links = [
        ['Manifest', artifactUrl(data.manifest_path)],
        ['CSS', artifactUrl(data.css_path)],
        ['Remotion', artifactUrl(data.remotion_path)],
      ].filter(([, url]) => url).map(([label, url]) => `<a href="${url}" target="_blank">${label}</a>`).join('');
      container.innerHTML = `
        <div class="role-list">${roles}</div>
        <div class="artifact-links">${links}</div>
      `;
    }

    function renderTemplateBundle(data) {
      const container = document.getElementById('templateOut');
      const bundle = data.template_bundle;
      const urls = data.template_urls || {};
      if (!bundle) {
        container.innerHTML = '<div class="empty">템플릿 번들이 아직 없습니다.</div>';
        return;
      }
      const assets = Object.entries(bundle.asset_paths || {}).map(([role, path]) => `
        <span class="tag">${esc(role)} · ${esc(path.split('/').slice(-1)[0])}</span>
      `).join('');
      container.innerHTML = `
        <div class="summary-grid">
          <div class="summary-card">
            <strong>Bundle Output</strong>
            <div>랜딩, 썸네일, 포스터 템플릿이 self-contained 형태로 생성됩니다.</div>
            <small>${esc(bundle.bundle_dir || '')}</small>
          </div>
          <div class="summary-card">
            <strong>Bundled Assets</strong>
            <div class="tag-list">${assets || '<span class="tag">asset 없음</span>'}</div>
          </div>
        </div>
        <div class="bundle-links">
          <a href="${urls.landing_url || '#'}" target="_blank">Landing</a>
          <a href="${urls.thumbnail_url || '#'}" target="_blank">Thumbnail</a>
          <a href="${urls.poster_url || '#'}" target="_blank">Poster</a>
          <a href="${urls.css_url || '#'}" target="_blank">CSS</a>
          <a href="${urls.manifest_url || '#'}" target="_blank">Manifest</a>
        </div>
      `;
    }

    function renderHandoffSummary(data) {
      const container = document.getElementById('handoffSummary');
      if (!data || !data.font_system) {
        container.innerHTML = '<div class="empty">디자인 에이전트용 handoff가 아직 없습니다.</div>';
        return;
      }
      const hints = data.hints || {};
      const roles = data.font_system.roles || {};
      const boundary = (data.design_agent_handoff || {}).collaboration_boundary || {};
      const roleList = Object.entries(roles).map(([name, role]) => `
        <article class="role-card">
          <strong>${esc(name)}</strong>
          <h4>${esc(role.family)}</h4>
          <div class="license-pill ${esc(licenseProfileStatus(role.license_profile || {}))}">${esc(licenseBadgeLabel(role.license_profile || {}))}</div>
          <span class="license-detail">${esc(role.license_summary || licenseBadgeDetail(role.license_profile || {}))}</span>
        </article>
      `).join('');
      container.innerHTML = `
        <div class="summary-grid">
          <div class="summary-card">
            <strong>Use Case</strong>
            <div>${esc(data.medium || 'n/a')} / ${esc(data.surface || 'n/a')} / ${esc(data.primary_role || 'n/a')}</div>
            <small>${esc((data.tones || []).join(', ') || 'tone 없음')}</small>
          </div>
          <div class="summary-card">
            <strong>Guidance</strong>
            ${renderLines(data.guidance || [])}
          </div>
        </div>
        <div class="role-list" style="margin-top:12px;">${roleList}</div>
        <div class="hint-group" style="margin-top:12px;">
          <article class="hint-card">
            <strong>Type Scale</strong>
            <div>${esc((hints.type_scale || {}).title_to_subtitle_ratio || 'n/a')} / ${esc((hints.type_scale || {}).subtitle_to_body_ratio || 'n/a')}</div>
            ${renderLines((hints.type_scale || {}).notes || [])}
          </article>
          <article class="hint-card">
            <strong>Contrast</strong>
            <div>${esc((hints.contrast || {}).recommended_mode || 'n/a')}</div>
            ${renderLines([(hints.contrast || {}).background_guidance].filter(Boolean).concat((hints.contrast || {}).notes || []))}
          </article>
          <article class="hint-card">
            <strong>Ratio</strong>
            <div>${esc((hints.ratio || {}).canvas_ratio || 'n/a')} · ${esc((hints.ratio || {}).title_block_width || 'n/a')}</div>
            ${renderLines((hints.ratio || {}).notes || [])}
          </article>
        </div>
        <div class="summary-grid" style="margin-top:12px;">
          <div class="summary-card">
            <strong>FontAgent Owns</strong>
            ${renderLines(boundary.font_agent_owns || [])}
          </div>
          <div class="summary-card">
            <strong>Design Agent Owns</strong>
            ${renderLines(boundary.design_agent_owns || [])}
          </div>
        </div>
        <div class="artifact-links">
          <a href="${artifactUrl(data.font_system.manifest_path)}" target="_blank">Manifest</a>
          <a href="${artifactUrl(data.font_system.css_path)}" target="_blank">CSS</a>
          <a href="${artifactUrl(data.font_system.remotion_path)}" target="_blank">Remotion</a>
        </div>
      `;
    }

    async function renderResults(results) {
      state.results = results || [];
      if (!state.results.length) {
        renderCompare([], []);
        return;
      }
      state.previews = await Promise.all(state.results.map((font) => enrichPreview(font.font_id, font.preview_preset)));
      renderCompare(state.results, state.previews);
    }

    async function runSearch() {
      const request = currentRequest();
      renderRequestSummary(request);
      const response = await fetch(`/fonts/search?query=${encodeURIComponent(request.query)}&language=${encodeURIComponent(request.language)}`);
      const data = await response.json();
      setMono('systemOut', data);
      await renderResults(data.results || []);
    }

    async function runRecommend() {
      const request = currentRequest();
      renderRequestSummary(request);
      const data = await postJson('/fonts/recommend', {
        task: request.task,
        language: request.language,
        count: 8,
        commercial_only: request.constraints.commercial_use,
        video_only: request.constraints.video_use,
      });
      setMono('systemOut', data);
      await renderResults(data.results || []);
    }

    async function runUseCaseRecommend() {
      const request = currentRequest();
      const data = await postJson('/fonts/recommend-use-case', {
        use_case: request.use_case,
        medium: request.medium,
        surface: request.surface,
        role: request.role,
        tones: request.tones,
        languages: request.language ? [request.language] : [],
        constraints: request.constraints,
        count: 8,
      });
      state.request = {
        ...(data.request || request),
        use_case: request.use_case,
        task: request.task,
        query: data.query || request.query,
      };
      renderRequestSummary(state.request);
      setMono('systemOut', data.request || data);
      await renderResults(data.results || []);
    }

    async function runInterviewRecommend() {
      const category = document.getElementById('interviewCategory').value;
      const subcategory = document.getElementById('interviewSubcategory').value;
      const language = document.getElementById('language').value || 'ko';
      const data = await postJson('/fonts/interview-recommend', {
        category,
        subcategory,
        answers: collectInterviewAnswers(),
        language,
        count: 8,
      });
      state.interviewData = data;
      state.request = {
        ...(data.request || {}),
        use_case: document.getElementById('useCase').value,
        task: data.query || document.getElementById('task').value,
      };
      syncRequestFields(data.request || null);
      if (data.query) {
        document.getElementById('task').value = data.query;
      }
      if ((data.recommended_copy || {}).title) {
        document.getElementById('sampleText').value = data.recommended_copy.title;
      }
      renderRequestSummary(data.request || null);
      renderInterviewCanvas(data);
      setMono('systemOut', data.font_system_preview || data);
      await renderResults(data.results || []);
    }

    async function installFont(fontId) {
      const outputDir = document.getElementById('installDir').value;
      const data = await postJson('/fonts/install', {font_id: fontId, output_dir: outputDir});
      setOptionalMono(`out-${fontId}`, data);
    }

    async function exportCss(fontId) {
      const data = await postJson('/fonts/export/css', {font_id: fontId});
      setOptionalMono(`out-${fontId}`, data.css || data);
    }

    async function exportRemotion(fontId) {
      const data = await postJson('/fonts/export/remotion', {font_id: fontId});
      setOptionalMono(`out-${fontId}`, data.remotion || data);
    }

    async function resolveDownload(fontId) {
      const data = await postJson('/fonts/resolve-download', {font_id: fontId});
      setOptionalMono(`out-${fontId}`, data);
    }

    async function prepareBrowserTask(fontId) {
      const outputDir = document.getElementById('browserTaskDir').value;
      const data = await postJson('/fonts/prepare-browser-task', {font_id: fontId, output_dir: outputDir});
      setOptionalMono(`out-${fontId}`, data);
    }

    async function prepareFontSystem(withTemplates = false) {
      const projectPath = document.getElementById('projectPath').value;
      const task = document.getElementById('task').value;
      const language = document.getElementById('language').value;
      const useCase = document.getElementById('useCase').value;
      const path = withTemplates ? '/fonts/generate-template-bundle' : '/fonts/prepare-font-system';
      const data = await postJson(path, {
        project_path: projectPath,
        task,
        language,
        use_case: useCase,
        target: 'both',
        with_templates: withTemplates,
      });
      state.system = data;
      setMono('systemOut', data);
      renderSystemSummary(data);
      renderTemplateBundle(data);
      openDrawer(withTemplates ? 'template' : 'system');
    }

    async function generateTemplateBundle() {
      await prepareFontSystem(true);
    }

    async function generateTypographyHandoff() {
      const projectPath = document.getElementById('projectPath').value;
      const task = document.getElementById('task').value;
      const language = document.getElementById('language').value;
      const useCase = document.getElementById('useCase').value;
      const data = await postJson('/fonts/generate-typography-handoff', {
        project_path: projectPath,
        task,
        language,
        use_case: useCase,
        target: 'both',
      });
      state.handoff = data;
      setMono('handoffOut', data);
      renderHandoffSummary(data);
      openDrawer('handoff');
    }

    async function copyPreview(url) {
      if (url) {
        await navigator.clipboard.writeText(url);
      }
    }

    document.getElementById('interviewCategory').addEventListener('change', updateInterviewSubcategories);
    document.getElementById('interviewSubcategory').addEventListener('change', renderInterviewQuestions);
    document.getElementById('useCase').addEventListener('change', (event) => {
      const value = event.target.value;
      if (QUICK_PRESETS[value]) {
        applyQuickPreset(value, {run: false});
        return;
      }
      state.activePreset = '';
      renderQuickPresets();
      renderPresetSummary('');
    });
    document.getElementById('catalogLanguage').addEventListener('change', refreshCatalog);
    document.getElementById('catalogPreset').addEventListener('change', refreshCatalog);
    document.getElementById('catalogCommercialOnly').addEventListener('change', refreshCatalog);
    document.getElementById('catalogVideoOnly').addEventListener('change', refreshCatalog);
    document.getElementById('catalogWebOnly').addEventListener('change', refreshCatalog);

    async function boot() {
      await loadUseCases();
      await loadInterviewCatalog();
      renderQuickPresets();
      renderPresetSummary('');
      applyQuickPreset('youtube-thumbnail-ko', {run: false});
      renderRequestSummary(currentRequest());
      renderInterviewCanvas(null);
      renderSystemSummary(null);
      renderTemplateBundle({});
      renderHandoffSummary(null);
      await runUseCaseRecommend();
      await refreshCatalog();
    }

    boot();
  </script>
</body>
</html>
"""


def resolve_recommend_use_case_payload(payload: dict) -> dict:
    use_case = payload.get("use_case") or ""
    medium = payload.get("medium", "")
    surface = payload.get("surface", "")
    role = payload.get("role", "")
    tones = payload.get("tones")
    if use_case:
        preset = get_use_case_preset(use_case)
        medium = medium or preset.get("medium", "")
        surface = surface or preset.get("surface", "")
        role = role or preset.get("role", "")
        if not tones:
            tones = preset.get("tones")
    return {
        "medium": medium,
        "surface": surface,
        "role": role,
        "tones": tones,
        "languages": payload.get("languages"),
        "constraints": payload.get("constraints"),
        "count": int(payload.get("count", 5)),
        "include_failed": payload.get("include_failed", False),
    }


def paginate_catalog_results(results: list[dict], page: int, page_size: int) -> dict:
    safe_page_size = max(1, page_size)
    total_count = len(results)
    total_pages = max(1, (total_count + safe_page_size - 1) // safe_page_size)
    safe_page = min(max(1, page), total_pages)
    start = (safe_page - 1) * safe_page_size
    end = start + safe_page_size
    return {
        "count": total_count,
        "page": safe_page,
        "page_size": safe_page_size,
        "total_pages": total_pages,
        "results": results[start:end],
    }


def make_handler(root: Path):
    service = FontAgentService(root)
    service.ensure_catalog_ready(auto_scan_system=True)

    class Handler(BaseHTTPRequestHandler):
        def _send_json(self, payload: dict, status: int = 200) -> None:
            data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _send_html(self, html: str, status: int = 200) -> None:
            data = html.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _send_file(self, path: Path, cache_control: str | None = None) -> None:
            if not path.exists():
                self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)
                return
            mime, _ = guess_type(str(path))
            data = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mime or "application/octet-stream")
            self.send_header("Content-Length", str(len(data)))
            if cache_control:
                self.send_header("Cache-Control", cache_control)
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            qs = parse_qs(parsed.query)
            if parsed.path == "/":
                self._send_html(INDEX_HTML)
                return
            if parsed.path == "/health":
                self._send_json({"ok": True})
                return
            if parsed.path == "/fonts/preview.svg":
                font_id = qs.get("font_id", [""])[0]
                if not font_id:
                    self._send_json({"error": "Missing font_id"}, status=HTTPStatus.BAD_REQUEST)
                    return
                preset = qs.get("preset", ["title-ko"])[0]
                preview = service.preview(
                    font_id,
                    preset,
                    sample_text=qs.get("sample_text", [""])[0] or None,
                )
                self._send_file(Path(preview["preview_path"]), cache_control="no-store")
                return
            if parsed.path == "/fonts/preview-asset":
                font_id = qs.get("font_id", [""])[0]
                if not font_id:
                    self._send_json({"error": "Missing font_id"}, status=HTTPStatus.BAD_REQUEST)
                    return
                asset = service.prepare_preview_font_asset(
                    font_id,
                    qs.get("preset", ["title-ko"])[0],
                )
                asset_path = asset.get("asset_path", "")
                if not asset_path:
                    self._send_json({"error": "Preview asset unavailable"}, status=HTTPStatus.NOT_FOUND)
                    return
                self._send_file(Path(asset_path), cache_control="no-store")
                return
            if parsed.path.startswith("/previews/"):
                filename = Path(parsed.path).name
                self._send_file(service.preview_dir / filename)
                return
            if parsed.path == "/artifacts":
                requested = qs.get("path", [""])[0]
                if not requested:
                    self._send_json({"error": "Missing path"}, status=HTTPStatus.BAD_REQUEST)
                    return
                self._send_file(Path(requested).expanduser())
                return
            if parsed.path == "/fonts/search":
                results = service.search(
                    query=qs.get("query", [""])[0],
                    language=qs.get("language", [None])[0],
                    commercial_only=qs.get("commercial_only", ["false"])[0] == "true",
                    video_only=qs.get("video_only", ["false"])[0] == "true",
                    web_embedding_only=qs.get("web_embedding_only", ["false"])[0] == "true",
                    detail_level=qs.get("detail", ["full"])[0],
                )
                self._send_json({"results": results})
                return
            if parsed.path == "/fonts/catalog":
                results = service.search(
                    query=qs.get("query", [""])[0],
                    language=qs.get("language", [None])[0],
                    commercial_only=qs.get("commercial_only", ["false"])[0] == "true",
                    video_only=qs.get("video_only", ["false"])[0] == "true",
                    web_embedding_only=qs.get("web_embedding_only", ["false"])[0] == "true",
                    detail_level=qs.get("detail", ["compact"])[0],
                )
                self._send_json(
                    paginate_catalog_results(
                        results,
                        page=int(qs.get("page", ["1"])[0]),
                        page_size=int(qs.get("page_size", ["20"])[0]),
                    )
                )
                return
            if parsed.path == "/fonts/use-cases":
                self._send_json(service.list_use_cases())
                return
            if parsed.path == "/fonts/interview-catalog":
                self._send_json(service.list_interview_catalog())
                return
            self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")

            def with_artifact_urls(data: dict) -> dict:
                bundle = data.get("template_bundle")
                if not bundle:
                    return data
                data = dict(data)
                data["template_urls"] = {
                    "landing_url": f"/artifacts?path={quote(bundle['landing_path'])}",
                    "thumbnail_url": f"/artifacts?path={quote(bundle['thumbnail_path'])}",
                    "poster_url": f"/artifacts?path={quote(bundle['poster_path'])}",
                    "css_url": f"/artifacts?path={quote(bundle['css_path'])}",
                    "manifest_url": f"/artifacts?path={quote(bundle['manifest_path'])}",
                }
                return data
            try:
                if parsed.path == "/fonts/recommend":
                    results = service.recommend(
                        task=payload.get("task", ""),
                        language=payload.get("language"),
                        commercial_only=payload.get("commercial_only", True),
                        video_only=payload.get("video_only", False),
                        count=int(payload.get("count", 5)),
                    )
                    self._send_json({"results": results})
                    return
                if parsed.path == "/fonts/recommend-use-case":
                    use_case_payload = resolve_recommend_use_case_payload(payload)
                    self._send_json(
                        service.recommend_use_case(
                            medium=use_case_payload["medium"],
                            surface=use_case_payload["surface"],
                            role=use_case_payload["role"],
                            tones=use_case_payload["tones"],
                            languages=use_case_payload["languages"],
                            constraints=use_case_payload["constraints"],
                            count=use_case_payload["count"],
                            include_failed=use_case_payload["include_failed"],
                        )
                    )
                    return
                if parsed.path == "/fonts/interview-recommend":
                    self._send_json(
                        service.guided_interview_recommend(
                            category=payload.get("category", ""),
                            subcategory=payload.get("subcategory", ""),
                            answers=payload.get("answers"),
                            language=payload.get("language", "ko"),
                            count=int(payload.get("count", 6)),
                            include_failed=payload.get("include_failed", False),
                        )
                    )
                    return
                if parsed.path == "/fonts/preview":
                    preset = payload.get("preset", "title-ko")
                    font_id = payload["font_id"]
                    preview = service.preview(
                        font_id,
                        preset,
                        sample_text=payload.get("sample_text"),
                    )
                    preview_name = Path(preview["preview_path"]).name
                    preview["preview_url"] = f"/previews/{preview_name}"
                    self._send_json(preview)
                    return
                if parsed.path == "/fonts/install":
                    output_dir = Path(payload.get("output_dir", "./installed_fonts"))
                    self._send_json(service.install(payload["font_id"], output_dir))
                    return
                if parsed.path == "/fonts/resolve-download":
                    self._send_json(service.resolve_download(payload["font_id"]))
                    return
                if parsed.path == "/fonts/prepare-browser-task":
                    self._send_json(
                        service.prepare_browser_download_task(
                            payload["font_id"],
                            Path(payload.get("output_dir", "./browser_tasks")),
                        )
                    )
                    return
                if parsed.path == "/fonts/prepare-font-system":
                    self._send_json(
                        with_artifact_urls(
                            service.prepare_font_system(
                                project_path=Path(payload.get("project_path", "./demo-project")),
                                task=payload.get("task", ""),
                                language=payload.get("language", "ko"),
                                target=payload.get("target", "both"),
                                asset_dir=payload.get("asset_dir", "assets/fonts"),
                                use_case=payload.get("use_case") or None,
                                with_templates=payload.get("with_templates", False),
                            )
                        )
                    )
                    return
                if parsed.path == "/fonts/generate-template-bundle":
                    self._send_json(
                        with_artifact_urls(
                            service.generate_template_bundle(
                                project_path=Path(payload.get("project_path", "./demo-project")),
                                task=payload.get("task", ""),
                                language=payload.get("language", "ko"),
                                target=payload.get("target", "both"),
                                asset_dir=payload.get("asset_dir", "assets/fonts"),
                                use_case=payload.get("use_case") or None,
                            )
                        )
                    )
                    return
                if parsed.path == "/fonts/generate-typography-handoff":
                    self._send_json(
                        service.generate_typography_handoff(
                            project_path=Path(payload.get("project_path", "./demo-project")),
                            task=payload.get("task", ""),
                            language=payload.get("language", "ko"),
                            target=payload.get("target", "both"),
                            asset_dir=payload.get("asset_dir", "assets/fonts"),
                            use_case=payload.get("use_case") or None,
                        )
                    )
                    return
                if parsed.path == "/fonts/export/css":
                    self._send_json(service.export_css(payload["font_id"]))
                    return
                if parsed.path == "/fonts/export/remotion":
                    self._send_json(service.export_remotion(payload["font_id"]))
                    return
            except KeyError as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.NOT_FOUND)
                return
            self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

        def log_message(self, format: str, *args) -> None:
            return

    return Handler


def serve(root: Path, host: str = "127.0.0.1", port: int = 8123) -> None:
    server = ThreadingHTTPServer((host, port), make_handler(root))
    try:
        server.serve_forever()
    finally:
        server.server_close()
