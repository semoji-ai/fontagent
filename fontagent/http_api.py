from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from mimetypes import guess_type
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

from .service import FontAgentService


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
    .page { max-width: 1600px; margin: 0 auto; padding: 28px 20px 56px; }
    .hero {
      display: grid;
      grid-template-columns: minmax(0, 1.2fr) minmax(360px, 0.8fr);
      gap: 18px;
      margin-bottom: 18px;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 24px;
      padding: 20px;
      box-shadow: var(--shadow);
    }
    .hero-copy h1 {
      margin: 0 0 10px;
      font-size: clamp(42px, 5vw, 68px);
      line-height: 0.96;
      letter-spacing: -0.04em;
    }
    .hero-copy p,
    .panel p {
      margin: 0;
      color: var(--muted);
      line-height: 1.58;
    }
    .hero-meta {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
      margin-top: 18px;
    }
    .metric {
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 14px;
      background: rgba(255,255,255,0.75);
    }
    .metric strong {
      display: block;
      font-size: 12px;
      color: var(--muted);
      margin-bottom: 6px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }
    .metric span {
      font-size: 15px;
      font-weight: 700;
      line-height: 1.35;
    }
    .workspace {
      display: grid;
      grid-template-columns: 380px minmax(0, 1fr);
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
      aspect-ratio: 1200 / 630;
      background: #faf7ef;
      border-bottom: 1px solid var(--line);
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
    .results {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 16px;
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
      .workspace { grid-template-columns: 340px minmax(0, 1fr); }
    }
    @media (max-width: 980px) {
      .hero,
      .workspace { grid-template-columns: 1fr; }
      .rail { position: static; }
      .stack-2,
      .stack-3 { grid-template-columns: 1fr; }
      .hero-meta { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="page">
    <section class="hero">
      <article class="panel hero-copy">
        <h1>FontAgent</h1>
        <p>폰트 특화 에이전트의 역할은 “예쁜 결과 만들기”보다 타이포 의사결정을 돕고, 라이선스를 검토하고, 프로젝트에 적용 가능한 폰트 시스템을 만들어 디자인 에이전트로 넘기는 것입니다.</p>
        <div class="hero-meta">
          <div class="metric">
            <strong>Decision Console</strong>
            <span>입력 조건, 후보 비교, 프로젝트 handoff를 한 화면에서 정리합니다.</span>
          </div>
          <div class="metric">
            <strong>Typography Scope</strong>
            <span>검색, 추천, 라이선스, 페어링, 설치, font system까지 담당합니다.</span>
          </div>
          <div class="metric">
            <strong>Collaboration</strong>
            <span>레이아웃과 컬러는 디자인 에이전트가 맡고, FontAgent는 타이포 시스템을 넘깁니다.</span>
          </div>
        </div>
      </article>
      <article class="panel">
        <div class="section-title">
          <h2>현재 작업 초점</h2>
          <span>Typography First</span>
        </div>
        <div class="summary-grid">
          <div class="summary-card">
            <strong>Search</strong>
            <div>매체, 역할, 톤, 라이선스 조건을 기준으로 좁힙니다.</div>
          </div>
          <div class="summary-card">
            <strong>Compare</strong>
            <div>같은 문구를 나란히 보여줘서 display 적합도를 빠르게 비교합니다.</div>
          </div>
          <div class="summary-card">
            <strong>Handoff</strong>
            <div>font system, hints, collaboration boundary를 디자인 에이전트에게 넘깁니다.</div>
          </div>
        </div>
      </article>
    </section>

    <section class="workspace">
      <aside class="rail left">
        <section class="panel">
          <div class="section-title">
            <h3>가이드 인터뷰</h3>
            <span>Guided Intake</span>
          </div>
          <div class="controls">
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
          </div>
        </section>

        <section class="panel">
          <div class="section-title">
            <h3>입력 조건</h3>
            <span>Search / Recommend</span>
          </div>
          <div class="controls">
            <div>
              <label class="label" for="query">Search Query</label>
              <input id="query" value="documentary title" placeholder="예: documentary subtitle serif" />
            </div>
            <div class="stack-2">
              <div>
                <label class="label" for="language">Language</label>
                <input id="language" value="ko" placeholder="ko / en" />
              </div>
              <div>
                <label class="label" for="useCase">Use Case</label>
                <select id="useCase">
                  <option value="">직접 task 사용</option>
                  <option value="documentary-landing-ko">다큐 랜딩 페이지</option>
                  <option value="youtube-thumbnail-ko">유튜브 썸네일</option>
                  <option value="poster-headline">포스터 헤드라인</option>
                  <option value="presentation-cover">프레젠테이션 커버</option>
                </select>
              </div>
            </div>
            <div>
              <label class="label" for="task">Task</label>
              <textarea id="task">history documentary title</textarea>
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
              <input id="tones" value="cinematic,retro" placeholder="cinematic, retro, editorial" />
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
              <button onclick="runSearch()">검색</button>
              <button class="secondary" onclick="runRecommend()">task 추천</button>
            </div>
            <button class="ghost" onclick="runUseCaseRecommend()">구조화 용도 추천</button>
            <details>
              <summary>고급 설정 / 출력 경로</summary>
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

        <section class="panel">
          <div class="section-title">
            <h3>폰트 리스트</h3>
            <span>Preview / Actions</span>
          </div>
          <div id="results" class="results"></div>
        </section>
      </aside>

      <main class="main">
        <section class="panel">
          <div class="section-title">
            <h2>요청 요약</h2>
            <span>Request Brief</span>
          </div>
          <div id="requestSummary" class="empty">검색이나 추천을 실행하면 현재 medium, surface, role, tone, 라이선스 조건이 이 영역에 정리됩니다.</div>
        </section>

        <section class="panel">
          <div class="section-title">
            <h2>기본 타이포 캔버스</h2>
            <span>Guided Preview</span>
          </div>
          <div id="interviewCanvas" class="empty">카테고리와 세부 카테고리를 고른 뒤 인터뷰 기반 추천을 실행하면, 기본 레이아웃과 role별 폰트 시스템이 여기에 배치됩니다.</div>
          <div class="canvas-toolbar">
            <button class="secondary" onclick="prepareFontSystem()">폰트 시스템 보기</button>
            <button onclick="generateTemplateBundle()">템플릿 보기</button>
            <button class="secondary" onclick="generateTypographyHandoff()">handoff 보기</button>
          </div>
        </section>

        <section class="panel">
          <div class="section-title">
            <h2>비교 미리보기</h2>
            <span>Compare Candidates</span>
          </div>
          <div id="compare" class="compare-wrap empty">상위 후보를 같은 문구로 나란히 보여줍니다.</div>
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
      container.innerHTML = `
        <div class="summary-grid">
          <div class="summary-card">
            <strong>Primary Context</strong>
            <div>${esc(request.medium || 'n/a')} / ${esc(request.surface || 'n/a')} / ${esc(request.role || 'n/a')}</div>
            <small>${esc(request.task || request.query || '')}</small>
          </div>
          <div class="summary-card">
            <strong>Language & Use Case</strong>
            <div>${esc(primaryLanguage)} · ${esc(request.use_case || 'custom')}</div>
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
            <span>${esc(font.source_site || '')} · ${esc(font.license_summary || '')}</span>
            ${renderLines((font.why || []).slice(0, 2))}
          </div>
        </article>
      `).join('');
      container.innerHTML = `<div class="compare-grid">${cards}</div>`;
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
          <p>${esc(role.generic_family || '')} · ${esc(role.source_site || '')} · ${esc(role.license_summary || '')}</p>
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
          <p>${esc(role.license_summary || '')}</p>
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
      const container = document.getElementById('results');
      state.results = results || [];
      if (!state.results.length) {
        container.innerHTML = '<div class="empty">결과가 없습니다.</div>';
        renderCompare([], []);
        return;
      }
      state.previews = await Promise.all(state.results.map((font) => enrichPreview(font.font_id, font.preview_preset)));
      renderCompare(state.results, state.previews);
      container.innerHTML = state.results.map((font, index) => {
        const previewUrl = state.previews[index] || '';
        const licenseProfile = font.license_profile || {};
        const automationProfile = font.automation_profile || {};
        return `
          <article class="result-card">
            <img src="${previewUrl}" alt="${esc(font.family)} preview" />
            <div class="body">
              <h3>${esc(font.family)}</h3>
              <span class="result-meta">${esc(font.source_site || '')} · ${esc(font.license_summary || '')}</span>
              <div class="tag-list">
                <span class="tag">license ${esc(licenseProfile.status || 'n/a')}</span>
                <span class="tag">confidence ${esc(licenseProfile.confidence || 'n/a')}</span>
                <span class="tag">automation ${esc(automationProfile.status || 'n/a')}</span>
              </div>
              <div class="tag-list">${renderTagList((font.tags || []).concat(font.recommended_for || []).slice(0, 10))}</div>
              ${renderLines((font.why || []).slice(0, 3))}
              <details>
                <summary>raw / actions</summary>
                <pre id="out-${esc(font.font_id)}" class="mono">font_id: ${esc(font.font_id)}</pre>
                <div class="card-actions">
                  <button onclick="installFont('${esc(font.font_id)}')">설치</button>
                  <button class="secondary" onclick="exportCss('${esc(font.font_id)}')">CSS</button>
                  <button class="secondary" onclick="exportRemotion('${esc(font.font_id)}')">Remotion</button>
                  <button class="secondary" onclick="resolveDownload('${esc(font.font_id)}')">Resolve</button>
                  <button class="secondary" onclick="prepareBrowserTask('${esc(font.font_id)}')">Browser Task</button>
                  <button class="ghost" onclick="copyPreview('${previewUrl}')">Preview URL</button>
                </div>
              </details>
            </div>
          </article>
        `;
      }).join('');
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
        medium: request.medium,
        surface: request.surface,
        role: request.role,
        tones: request.tones,
        languages: request.language ? [request.language] : [],
        constraints: request.constraints,
        count: 8,
      });
      state.request = data.request || request;
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
      state.request = data.request || null;
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
      setMono(`out-${fontId}`, data);
    }

    async function exportCss(fontId) {
      const data = await postJson('/fonts/export/css', {font_id: fontId});
      setMono(`out-${fontId}`, data.css || data);
    }

    async function exportRemotion(fontId) {
      const data = await postJson('/fonts/export/remotion', {font_id: fontId});
      setMono(`out-${fontId}`, data.remotion || data);
    }

    async function resolveDownload(fontId) {
      const data = await postJson('/fonts/resolve-download', {font_id: fontId});
      setMono(`out-${fontId}`, data);
    }

    async function prepareBrowserTask(fontId) {
      const outputDir = document.getElementById('browserTaskDir').value;
      const data = await postJson('/fonts/prepare-browser-task', {font_id: fontId, output_dir: outputDir});
      setMono(`out-${fontId}`, data);
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

    async function boot() {
      await loadInterviewCatalog();
      renderRequestSummary(currentRequest());
      renderInterviewCanvas(null);
      renderSystemSummary(null);
      renderTemplateBundle({});
      renderHandoffSummary(null);
      await runInterviewRecommend();
    }

    boot();
  </script>
</body>
</html>
"""


def make_handler(root: Path):
    service = FontAgentService(root)

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

        def _send_file(self, path: Path) -> None:
            if not path.exists():
                self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)
                return
            mime, _ = guess_type(str(path))
            data = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mime or "application/octet-stream")
            self.send_header("Content-Length", str(len(data)))
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
                )
                self._send_json({"results": results})
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
                    self._send_json(
                        service.recommend_use_case(
                            medium=payload.get("medium", ""),
                            surface=payload.get("surface", ""),
                            role=payload.get("role", ""),
                            tones=payload.get("tones"),
                            languages=payload.get("languages"),
                            constraints=payload.get("constraints"),
                            count=int(payload.get("count", 5)),
                            include_failed=payload.get("include_failed", False),
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
                    preview = service.preview(
                        payload["font_id"],
                        payload.get("preset", "title-ko"),
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
