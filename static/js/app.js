/**
 * QuickDiagnosis - Enhanced Client Application Logic
 * Matches the user interface in the reference screenshot
 */

class QuickDiagnosisApp {
  constructor() {
    this.state = {
      theme: localStorage.getItem('qd_theme') || 'light',
      userName: (localStorage.getItem('qd_user_name') && !['Homo', 'Friend'].includes(localStorage.getItem('qd_user_name'))) ? localStorage.getItem('qd_user_name') : 'there',
      patient: {
        gender: 'female',
        age: 25,
        weight: 62
      },
      selectedSymptoms: new Set(),
      activeFilterSystems: new Set(),
      systems: [],
      symptomsBySystem: {},
      symptomNameMap: {},
      deferredPwaPrompt: null,
      labReports: [],
      labDefinitions: [],
      attachedLabReportId: null,
      currentModalReportId: null,
      activeLabTab: 'history',
      addReportMode: 'file',
      manualTestRowCount: 0
    };

    // DOM Views
    this.views = {
      welcome: document.getElementById('view-welcome'),
      step1: document.getElementById('view-step1'),
      diagnosis: document.getElementById('view-diagnosis'),
      results: document.getElementById('view-results'),
      labReports: document.getElementById('view-lab-reports')
    };
  }

  async init() {
    this.applyTheme(this.state.theme);
    this.initPwa();
    this.initUserName();
    await this.loadConfig();
    await this.loadSymptoms();
    await this.loadLabDefinitions();
    await this.loadLabReports();
  }

  // -------------------------------------------------------------------------
  // Theme Switching (Light / Dark Mode)
  // -------------------------------------------------------------------------
  toggleTheme() {
    const nextTheme = this.state.theme === 'light' ? 'dark' : 'light';
    this.applyTheme(nextTheme);
  }

  applyTheme(theme) {
    this.state.theme = theme;
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('qd_theme', theme);
  }

  // -------------------------------------------------------------------------
  // User Name Greeting
  // -------------------------------------------------------------------------
  initUserName() {
    const stored = localStorage.getItem('qd_user_name');
    if (stored === 'Homo' || stored === 'Friend' || !stored) {
      this.state.userName = 'there';
      localStorage.setItem('qd_user_name', 'there');
    }
    const el = document.getElementById('user-display-name');
    if (el) el.textContent = this.state.userName;
  }

  promptUserName() {
    const name = prompt('What is your name?', this.state.userName);
    if (name && name.trim()) {
      this.state.userName = name.trim();
      localStorage.setItem('qd_user_name', this.state.userName);
      this.initUserName();
    }
  }

  // -------------------------------------------------------------------------
  // Progressive Web App Setup
  // -------------------------------------------------------------------------
  initPwa() {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js').catch(() => {});
    }

    const pwaBtn = document.getElementById('pwa-install-btn');
    window.addEventListener('beforeinstallprompt', (e) => {
      e.preventDefault();
      this.state.deferredPwaPrompt = e;
      if (pwaBtn) {
        pwaBtn.classList.remove('hidden');
        pwaBtn.onclick = () => {
          if (this.state.deferredPwaPrompt) {
            this.state.deferredPwaPrompt.prompt();
            this.state.deferredPwaPrompt = null;
            pwaBtn.classList.add('hidden');
          }
        };
      }
    });
  }

  // -------------------------------------------------------------------------
  // Data Loading
  // -------------------------------------------------------------------------
  async loadConfig() {
    try {
      const res = await fetch('/api/config');
      const data = await res.json();
      this.state.systems = data.body_systems || [];
    } catch (e) {
      console.warn('Config load fallback:', e);
    }
  }

  async loadSymptoms() {
    try {
      const res = await fetch('/api/symptoms');
      const data = await res.json();
      this.state.symptomsBySystem = data.symptoms_by_system || {};

      // Map lookup
      for (const [sys, list] of Object.entries(this.state.symptomsBySystem)) {
        list.forEach(s => {
          this.state.symptomNameMap[s.id] = s.name;
        });
      }

      const totalCount = Object.values(this.state.symptomsBySystem).reduce((acc, l) => acc + l.length, 0);
      const totalEl = document.getElementById('total-symptoms-count');
      if (totalEl) totalEl.textContent = `${totalCount} available`;

      this.renderSymptomsAccordions();
    } catch (e) {
      console.error('Symptoms load error:', e);
    }
  }

  // -------------------------------------------------------------------------
  // View Navigation (Step 1 -> Step 2 -> Step 3 Flow)
  // -------------------------------------------------------------------------
  showWelcomeView() {
    this.views.welcome.classList.remove('hidden');
    if (this.views.step1) this.views.step1.classList.add('hidden');
    this.views.diagnosis.classList.add('hidden');
    this.views.results.classList.add('hidden');
    if (this.views.labReports) this.views.labReports.classList.add('hidden');
    this.updateNavLinks('home');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  showStep1View() {
    this.views.welcome.classList.add('hidden');
    if (this.views.step1) this.views.step1.classList.remove('hidden');
    this.views.diagnosis.classList.add('hidden');
    this.views.results.classList.add('hidden');
    if (this.views.labReports) this.views.labReports.classList.add('hidden');
    this.syncStep1Controls();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  showDiagnosisView() {
    this.views.welcome.classList.add('hidden');
    if (this.views.step1) this.views.step1.classList.add('hidden');
    this.views.diagnosis.classList.remove('hidden');
    this.views.results.classList.add('hidden');
    if (this.views.labReports) this.views.labReports.classList.add('hidden');
    this.updateNavLinks('diagnosis');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  startDiagnosis() {
    // Asked FIRST: Step 1 (Personal Details: Gender, Age, Weight)
    this.showStep1View();
  }

  showResultsView() {
    this.views.welcome.classList.add('hidden');
    if (this.views.step1) this.views.step1.classList.add('hidden');
    this.views.diagnosis.classList.add('hidden');
    this.views.results.classList.remove('hidden');
    if (this.views.labReports) this.views.labReports.classList.add('hidden');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  showLabReportsView(tab = 'history') {
    this.views.welcome.classList.add('hidden');
    if (this.views.step1) this.views.step1.classList.add('hidden');
    this.views.diagnosis.classList.add('hidden');
    this.views.results.classList.add('hidden');
    if (this.views.labReports) this.views.labReports.classList.remove('hidden');
    this.updateNavLinks('labs');
    this.switchLabTab(tab);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  updateNavLinks(activeName) {
    const homeLink = document.getElementById('nav-link-home');
    const labsLink = document.getElementById('nav-link-labs');
    if (homeLink) homeLink.classList.toggle('active', activeName === 'home');
    if (labsLink) labsLink.classList.toggle('active', activeName === 'labs');
  }

  // -------------------------------------------------------------------------
  // Step 1: Personal Details Handlers
  // -------------------------------------------------------------------------
  syncStep1Controls() {
    const { gender, age, weight } = this.state.patient;
    this.step1SelectGender(gender, false);

    const ageInput = document.getElementById('step1-age-range');
    const ageDisp = document.getElementById('step1-age-display');
    if (ageInput) ageInput.value = age;
    if (ageDisp) ageDisp.textContent = `${age} years`;

    const weightInput = document.getElementById('step1-weight-range');
    const weightDisp = document.getElementById('step1-weight-display');
    if (weightInput) weightInput.value = weight;
    if (weightDisp) weightDisp.textContent = `${weight} kg`;
  }

  step1SelectGender(gender, updateState = true) {
    if (updateState) {
      this.state.patient.gender = gender;
    }
    ['female', 'male', 'other'].forEach(g => {
      const btn = document.getElementById(`step1-gender-${g}`);
      if (btn) {
        if (g === gender) btn.classList.add('active');
        else btn.classList.remove('active');
      }
    });
  }

  step1OnAgeChange(val) {
    this.state.patient.age = parseInt(val, 10);
    const disp = document.getElementById('step1-age-display');
    if (disp) disp.textContent = `${val} years`;
  }

  step1OnWeightChange(val) {
    this.state.patient.weight = parseInt(val, 10);
    const disp = document.getElementById('step1-weight-display');
    if (disp) disp.textContent = `${val} kg`;
  }

  completeStep1AndProceed() {
    // Calibrate gender and demographics
    this.setGender(this.state.patient.gender);
    this.updateSidebarDemographics();
    // Seamlessly proceed to Step 2: Select Symptoms
    this.showDiagnosisView();
  }

  // -------------------------------------------------------------------------
  // Gender Selection & Demographic Sync
  // -------------------------------------------------------------------------
  setGender(gender) {
    this.state.patient.gender = gender;
    
    const tabF = document.getElementById('tab-female');
    const tabM = document.getElementById('tab-male');
    const reprTag = document.getElementById('repr-tag-label');

    if (gender === 'female') {
      tabF.classList.add('active');
      tabM.classList.remove('active');
      if (reprTag) reprTag.textContent = 'Reproductive System (Female)';
    } else {
      tabM.classList.add('active');
      tabF.classList.remove('active');
      if (reprTag) reprTag.textContent = 'Reproductive System (Male)';
    }

    this.updateSidebarDemographics();
  }

  updateSidebarDemographics() {
    const g = document.getElementById('sb-patient-gender');
    const a = document.getElementById('sb-patient-age');
    const w = document.getElementById('sb-patient-weight');
    
    if (g) g.textContent = this.state.patient.gender === 'female' ? '♀ Female' : '♂ Male';
    if (a) a.textContent = `${this.state.patient.age} yrs`;
    if (w) w.textContent = `${this.state.patient.weight} kg`;
  }

  // -------------------------------------------------------------------------
  // Organ Hotspots & Callout Tags Filtering (Supports Multiple Systems)
  // -------------------------------------------------------------------------
  filterBySystem(systemId) {
    // Toggle system in/out of multi-select set
    if (this.state.activeFilterSystems.has(systemId)) {
      this.state.activeFilterSystems.delete(systemId);
    } else {
      this.state.activeFilterSystems.add(systemId);
    }

    // Highlight all currently selected organ tag buttons
    document.querySelectorAll('.organ-tag').forEach(tag => {
      const sid = tag.dataset.system;
      if (this.state.activeFilterSystems.has(sid)) {
        tag.classList.add('active');
      } else {
        tag.classList.remove('active');
      }
    });

    // Update filter active bar
    const bar = document.getElementById('filter-active-bar');
    const nameEl = document.getElementById('filter-system-name');
    if (bar && nameEl) {
      if (this.state.activeFilterSystems.size > 0) {
        bar.classList.remove('hidden');
        const names = Array.from(this.state.activeFilterSystems).map(sid => {
          const sysObj = this.state.systems.find(s => s.id === sid);
          return sysObj ? sysObj.name : sid;
        });
        nameEl.textContent = `${names.join(', ')} (${this.state.activeFilterSystems.size} selected)`;
      } else {
        bar.classList.add('hidden');
      }
    }

    // Render symptoms showing all selected systems
    this.renderSymptomsAccordions();
  }

  showAllSymptoms() {
    this.state.activeFilterSystems.clear();
    document.querySelectorAll('.organ-tag').forEach(t => t.classList.remove('active'));
    const bar = document.getElementById('filter-active-bar');
    if (bar) bar.classList.add('hidden');
    this.renderSymptomsAccordions();
  }

  // -------------------------------------------------------------------------
  // Symptoms Accordions Rendering & Interaction
  // -------------------------------------------------------------------------
  renderSymptomsAccordions(searchQuery = '') {
    const container = document.getElementById('symptom-accordions-list');
    if (!container) return;
    container.innerHTML = '';

    const systemKeys = Object.keys(this.state.symptomsBySystem);
    const hasFilter = this.state.activeFilterSystems.size > 0;

    systemKeys.forEach(sysId => {
      // If filtering by specific organs, only show matching categories (+ general)
      if (hasFilter && !this.state.activeFilterSystems.has(sysId) && sysId !== 'general') {
        return;
      }

      let symptoms = this.state.symptomsBySystem[sysId] || [];

      // If searching, filter symptoms by name
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        symptoms = symptoms.filter(s => s.name.toLowerCase().includes(q));
      }

      if (symptoms.length === 0) return;

      const sysMeta = this.state.systems.find(s => s.id === sysId);
      const categoryName = sysMeta ? sysMeta.name : (sysId.charAt(0).toUpperCase() + sysId.slice(1));
      const icon = sysMeta ? sysMeta.icon : '🩺';

      const box = document.createElement('div');
      box.className = 'category-accordion-box';
      box.id = `cat-box-${sysId}`;

      // Build header
      box.innerHTML = `
        <div class="cat-header" onclick="app.toggleCategory('${sysId}')">
          <div class="cat-name-group">
            <span>${icon}</span>
            <span>${categoryName}</span>
          </div>
          <span class="cat-chevron" id="chevron-${sysId}">⌄</span>
        </div>
        <div class="cat-symptoms-grid" id="grid-${sysId}"></div>
      `;

      // Build chips grid
      const grid = box.querySelector(`#grid-${sysId}`);
      symptoms.forEach(sym => {
        const isSelected = this.state.selectedSymptoms.has(sym.id);
        const chip = document.createElement('div');
        chip.className = `symptom-card-chip ${isSelected ? 'selected' : ''}`;
        chip.dataset.symptomId = sym.id;
        chip.innerHTML = `
          <span class="sym-emoji">${sym.icon || '•'}</span>
          <span class="sym-title">${sym.name}</span>
        `;
        chip.onclick = () => this.toggleSymptom(sym.id);
        grid.appendChild(chip);
      });

      container.appendChild(box);
    });

    if (container.children.length === 0) {
      container.innerHTML = '<div style="padding: 1.5rem; text-align: center; color: var(--text-muted);">No symptoms match your search.</div>';
    }
  }

  toggleCategory(sysId) {
    const box = document.getElementById(`cat-box-${sysId}`);
    if (box) box.classList.toggle('collapsed');
  }

  toggleSymptom(symptomId) {
    if (this.state.selectedSymptoms.has(symptomId)) {
      this.state.selectedSymptoms.delete(symptomId);
    } else {
      this.state.selectedSymptoms.add(symptomId);
    }

    // Sync chip visual state
    document.querySelectorAll(`.symptom-card-chip[data-symptom-id="${symptomId}"]`).forEach(chip => {
      chip.classList.toggle('selected', this.state.selectedSymptoms.has(symptomId));
    });

    this.updateSelectedCounter();
  }

  updateSelectedCounter() {
    const count = this.state.selectedSymptoms.size;
    const badge = document.getElementById('selected-count-badge');
    if (badge) badge.textContent = count;
  }

  onSearchInput(val) {
    const clearBtn = document.getElementById('clear-search-btn');
    if (clearBtn) {
      clearBtn.classList.toggle('hidden', !val.trim());
    }
    this.renderSymptomsAccordions(this.state.activeFilterSystem, val);
  }

  clearSearch() {
    const input = document.getElementById('symptom-search-input');
    if (input) input.value = '';
    const clearBtn = document.getElementById('clear-search-btn');
    if (clearBtn) clearBtn.classList.add('hidden');
    this.renderSymptomsAccordions(this.state.activeFilterSystem, '');
  }

  // -------------------------------------------------------------------------
  // Diagnosis Analysis & Probable Diseases
  // -------------------------------------------------------------------------
  async submitDiagnosis() {
    if (this.state.selectedSymptoms.size === 0) {
      alert('Please select at least 1 symptom to perform a health screening.');
      return;
    }

    const btn = document.getElementById('btn-analyze');
    if (btn) btn.innerHTML = '<span>Analyzing...</span>';

    try {
      const payload = {
        gender: this.state.patient.gender,
        age: this.state.patient.age,
        weight: this.state.patient.weight,
        symptoms: Array.from(this.state.selectedSymptoms),
        lab_report_id: this.state.attachedLabReportId || null
      };

      const res = await fetch('/api/diagnose', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await res.json();
      this.renderResults(data);
      this.showResultsView();
    } catch (err) {
      console.error('Diagnosis failed:', err);
      alert('Could not complete diagnosis. Please try again.');
    } finally {
      if (btn) btn.innerHTML = '<span>Diagnose</span><span>➔</span>';
    }
  }

  renderResults(data) {
    // 1. Quote
    const quoteEl = document.getElementById('results-quote-text');
    if (quoteEl && data.motivational_message) {
      quoteEl.textContent = `"${data.motivational_message}"`;
    }

    // 2. Patient summary line
    const summaryEl = document.getElementById('results-patient-summary');
    if (summaryEl) {
      const g = this.state.patient.gender === 'female' ? 'Female' : 'Male';
      const labBadge = data.has_lab_evidence ? ` • 🧪 Correlated with Lab Report (${data.attached_lab_abnormal_count} abnormal biomarkers)` : '';
      summaryEl.textContent = `Screening for: ${g}, ${this.state.patient.age} years, ${this.state.patient.weight} kg • ${data.selected_symptoms_count} symptoms reported${labBadge}`;
    }

    // 3. Diseases Grid
    const grid = document.getElementById('probable-diseases-grid');
    if (!grid) return;
    grid.innerHTML = '';

    const diseases = data.top_probable_diseases || [];
    if (diseases.length === 0) {
      grid.innerHTML = '<div style="padding: 2rem; text-align: center; color: var(--text-muted);">No common conditions match this exact cluster. Please consult a doctor.</div>';
      return;
    }

    diseases.forEach((dis, idx) => {
      const card = document.createElement('div');
      card.className = 'probable-card';

      const matchedList = dis.matched_core.concat(dis.matched_secondary).slice(0, 6)
        .map(s => `<span class="sym-tag-matched">✓ ${s}</span>`).join(' ');

      card.innerHTML = `
        <div class="probable-header">
          <div class="probable-title-group">
            <div class="disease-rank-num">#${idx + 1}</div>
            <div>
              <h3 class="probable-name">${dis.name}</h3>
              <div class="probable-meta">
                <span>${dis.category}</span>
                <span>•</span>
                <span class="urgency-badge urgency-${dis.urgency}">Urgency: ${dis.urgency}</span>
              </div>
            </div>
          </div>

          <div class="prob-metric-box">
            <div class="prob-score">${dis.probability_percentage}%</div>
            <div class="prob-label">Match Likelihood</div>
            <div class="prob-meter-bar">
              <div class="prob-meter-fill" style="width: ${dis.probability_percentage}%"></div>
            </div>
          </div>
        </div>

        <p style="font-size: 0.9rem; color: var(--text-muted); line-height: 1.5;">${dis.description}</p>

        <div class="symptoms-matched-strip">
          <span>Matched Symptoms:</span>
          ${matchedList || '<span>General overlap</span>'}
        </div>

        ${dis.has_lab_evidence && dis.matched_lab_findings && dis.matched_lab_findings.length > 0 ? `
          <div class="card-lab-findings-box">
            <div class="lab-findings-title">
              <span class="lab-findings-badge">🧪 Corroborating Laboratory Findings</span>
            </div>
            <div class="lab-findings-list">
              ${dis.matched_lab_findings.map(f => `
                <div class="lab-finding-item">
                  <div class="finding-top-row">
                    <span class="finding-name">${f.test_name}:</span>
                    <strong class="finding-val">${f.actual_value} ${f.unit}</strong>
                    <span class="status-pill status-${f.status.toLowerCase()}">${f.status}</span>
                    <span class="finding-sig-badge sig-${f.significance.toLowerCase()}">${f.significance}</span>
                  </div>
                  <div class="finding-desc">${f.explanation}</div>
                </div>
              `).join('')}
            </div>
          </div>
        ` : ''}

        ${dis.risk_explanation ? `
          <div style="background: rgba(37,99,235,0.08); border-left: 3px solid #2563eb; padding: 0.6rem 0.85rem; border-radius: 0 8px 8px 0; font-size: 0.8rem; color: var(--text-main);">
            <strong>Demographic Factor:</strong> ${dis.risk_explanation}
          </div>
        ` : ''}

        <!-- Authoritative Medical Information Source Strip -->
        <div class="card-source-strip">
          ${dis.external_source && dis.external_source.url ? `
            <div class="source-pill-group">
              <span class="source-badge-pill source-pill-nih">NIH / MedlinePlus</span>
              <a href="${dis.external_source.url}" target="_blank" rel="noopener noreferrer" class="source-link-chip" onclick="event.stopPropagation()">
                <span>${dis.external_source.title || 'Official Guide'}</span>
                <span class="ext-icon">↗</span>
              </a>
            </div>
          ` : `
            <div class="source-pill-group">
              <span class="source-badge-pill source-pill-local">Clinical Knowledge Base</span>
              <span class="source-local-note">Verified Local Dataset</span>
            </div>
          `}
        </div>

        <button class="card-cta-btn" onclick="app.openDiseaseDetail('${dis.id}')">
          <span>View Disease Guide &amp; Curing Measures</span>
          <span>➔</span>
        </button>
      `;

      grid.appendChild(card);
    });

    // Populate dedicated print report with patient details, diseases, and care tips
    this.renderPrintReport(data);
  }

  renderPrintReport(data) {
    const genderEl = document.getElementById('print-patient-gender');
    const ageEl = document.getElementById('print-patient-age');
    const weightEl = document.getElementById('print-patient-weight');
    const symptomsEl = document.getElementById('print-patient-symptoms');
    const diseasesListEl = document.getElementById('print-diseases-list');

    if (genderEl) {
      const g = this.state.patient.gender;
      genderEl.textContent = g === 'female' ? 'Female' : (g === 'male' ? 'Male' : 'Other');
    }
    if (ageEl) ageEl.textContent = `${this.state.patient.age} years`;
    if (weightEl) weightEl.textContent = `${this.state.patient.weight} kg`;

    if (symptomsEl) {
      symptomsEl.innerHTML = '';
      const selectedIds = Array.from(this.state.selectedSymptoms);
      if (selectedIds.length === 0) {
        symptomsEl.innerHTML = '<em>None specifically selected</em>';
      } else {
        selectedIds.forEach(id => {
          const chip = document.createElement('span');
          chip.className = 'print-sym-chip';
          chip.textContent = this.state.symptomNameMap[id] || id;
          symptomsEl.appendChild(chip);
        });
      }
    }

    if (diseasesListEl) {
      diseasesListEl.innerHTML = '';
      const diseases = data.top_probable_diseases || [];
      diseases.forEach((dis, idx) => {
        const item = document.createElement('div');
        item.className = 'print-disease-card';

        const homeTips = (dis.curing_measures?.immediate_home_measures || []).slice(0, 3);
        const dietTips = (dis.curing_measures?.diet_and_lifestyle || []).slice(0, 2);
        const warnTips = (dis.curing_measures?.when_to_see_doctor || []).slice(0, 1);

        item.innerHTML = `
          <div class="print-disease-head">
            <div>
              <span class="print-rank">#${idx + 1}</span>
              <span class="print-disease-name">${dis.name}</span>
              <span class="print-urgency">(${dis.urgency} Urgency)</span>
            </div>
            <div class="print-prob-score">${dis.probability_percentage}% Match</div>
          </div>
          <p class="print-disease-desc">${dis.description}</p>
          ${dis.risk_explanation ? `
            <div class="print-disease-context">
              <strong>Demographic Context:</strong> ${dis.risk_explanation}
            </div>
          ` : ''}
          <div class="print-disease-tips">
            <strong>Key Relief Measures &amp; Tips:</strong>
            <ul>
              ${homeTips.map(t => `<li><strong>Home Care:</strong> ${t}</li>`).join('')}
              ${dietTips.map(t => `<li><strong>Lifestyle/Diet:</strong> ${t}</li>`).join('')}
              ${warnTips.map(t => `<li class="print-alert-item"><strong>⚠️ See Doctor If:</strong> ${t}</li>`).join('')}
            </ul>
          </div>
        `;
        diseasesListEl.appendChild(item);
      });
    }
  }

  async refreshAffirmation() {
    try {
      const res = await fetch('/api/quote?context=after_result');
      const data = await res.json();
      const quoteEl = document.getElementById('results-quote-text');
      if (quoteEl && data.quote) {
        quoteEl.textContent = `"${data.quote}"`;
      }
    } catch (e) {}
  }

  // -------------------------------------------------------------------------
  // Disease In-Depth Detail Modal & Curing Measures (Core Requirement)
  // -------------------------------------------------------------------------
  async openDiseaseDetail(diseaseId) {
    const modal = document.getElementById('modal-disease-detail');
    if (!modal) return;
    modal.classList.remove('hidden');

    try {
      const res = await fetch(`/api/disease/${diseaseId}`);
      const data = await res.json();
      
      document.getElementById('detail-disease-name').textContent = data.name;
      document.getElementById('detail-category-badge').textContent = `${data.category} • ${data.system.toUpperCase()}`;
      
      const urg = document.getElementById('detail-urgency-badge');
      if (urg) {
        urg.className = `urgency-badge urgency-${data.urgency}`;
        urg.textContent = `Urgency: ${data.urgency}`;
      }

      // Populate Authoritative Medical Sources Section
      this.renderAuthoritativeSourceBanner(data);

      document.getElementById('detail-description').textContent = data.description;
      
      const demoRisk = document.getElementById('detail-demographic-risk');
      if (demoRisk) {
        demoRisk.textContent = data.demographic_risk?.risk_explanation || 'Affects varied demographics.';
      }

      const cures = data.measurements_and_cures || {};
      const ov = document.getElementById('detail-overview-text');
      if (ov && cures.overview) ov.textContent = cures.overview;

      this.populateList('detail-home-list', cures.immediate_home_measures);
      this.populateList('detail-diet-list', cures.dietary_lifestyle_adjustments);
      this.populateList('detail-med-list', cures.typical_medical_treatments);
      this.populateList('detail-warn-list', cures.when_to_see_doctor);
      this.populateList('detail-prev-list', cures.prevention_tips);

      // Populate FDA Medication Safety Section
      this.renderFDAMedicationSafety(data);
    } catch (err) {
      console.error('Error fetching disease:', err);
    }
  }

  renderAuthoritativeSourceBanner(data) {
    const badgesRow = document.getElementById('detail-source-badges');
    const sourceBody = document.getElementById('detail-source-body');
    if (!badgesRow || !sourceBody) return;

    badgesRow.innerHTML = '';
    sourceBody.innerHTML = '';

    const hasMedline = !!data.medlineplus;
    const hasFda = Array.isArray(data.fda_medications) && data.fda_medications.length > 0;

    if (hasMedline) {
      const b = document.createElement('span');
      b.className = 'source-badge-pill source-pill-nih';
      b.textContent = 'NIH / MedlinePlus';
      badgesRow.appendChild(b);
    }
    if (hasFda) {
      const b = document.createElement('span');
      b.className = 'source-badge-pill source-pill-fda';
      b.textContent = 'U.S. FDA / openFDA';
      badgesRow.appendChild(b);
    }
    const bBase = document.createElement('span');
    bBase.className = 'source-badge-pill source-pill-local';
    bBase.textContent = 'Clinical Knowledge Base';
    badgesRow.appendChild(bBase);

    // Build source details
    let contentHtml = '';
    if (hasMedline) {
      contentHtml += `
        <div class="source-record-row">
          <span class="source-icon">🏛️</span>
          <div class="source-meta">
            <span class="source-meta-label">Official Condition Topic:</span>
            <a href="${data.medlineplus.official_url}" target="_blank" rel="noopener noreferrer" class="source-meta-link">
              <strong>${data.medlineplus.title}</strong> — ${data.medlineplus.source_full || 'National Institutes of Health / NLM'}
              <span class="ext-icon">↗</span>
            </a>
          </div>
        </div>
      `;
    } else {
      contentHtml += `
        <div class="source-record-row">
          <span class="source-icon">📋</span>
          <div class="source-meta">
            <span class="source-meta-label">Primary Diagnostic Base:</span>
            <span class="source-meta-text">QuickDiagnosis Verified Clinical Dataset (Local Foundation)</span>
          </div>
        </div>
      `;
    }

    sourceBody.innerHTML = contentHtml;
  }

  renderFDAMedicationSafety(data) {
    const fdaContainer = document.getElementById('detail-fda-container');
    const fdaList = document.getElementById('detail-fda-list');
    if (!fdaContainer || !fdaList) return;

    const meds = data.fda_medications;
    if (!meds || !Array.isArray(meds) || meds.length === 0) {
      fdaContainer.classList.add('hidden');
      fdaList.innerHTML = '';
      return;
    }

    fdaContainer.classList.remove('hidden');
    fdaList.innerHTML = '';

    meds.forEach(med => {
      const card = document.createElement('div');
      card.className = 'fda-med-card';

      card.innerHTML = `
        <div class="fda-med-head">
          <div class="fda-med-title-group">
            <span class="fda-pill-symbol">💊</span>
            <strong>${med.drug_name}</strong>
            <span class="fda-generic-sub">(${med.generic_name})</span>
          </div>
          <a href="${med.official_url}" target="_blank" rel="noopener noreferrer" class="fda-official-link" title="View official drug label on openFDA">
            <span>openFDA Drug Label</span>
            <span class="ext-icon">↗</span>
          </a>
        </div>
        ${med.warnings ? `
          <div class="fda-alert-snippet">
            <span class="fda-warning-tag">⚠️ FDA Precautions &amp; Boxed Warnings:</span>
            <p>${med.warnings}</p>
          </div>
        ` : ''}
        ${med.indications ? `
          <div class="fda-indications-snippet">
            <span class="fda-indications-tag">Approved Indications:</span>
            <p>${med.indications}</p>
          </div>
        ` : ''}
      `;

      fdaList.appendChild(card);
    });
  }

  populateList(elementId, arr) {
    const el = document.getElementById(elementId);
    if (!el) return;
    el.innerHTML = '';
    (arr || []).forEach(item => {
      const li = document.createElement('li');
      li.textContent = item;
      el.appendChild(li);
    });
  }

  closeDiseaseDetailModal() {
    const modal = document.getElementById('modal-disease-detail');
    if (modal) modal.classList.add('hidden');
  }

  // -------------------------------------------------------------------------
  // Basic Details Modal (Personal Profile)
  // -------------------------------------------------------------------------
  openBasicDetailsModal() {
    const modal = document.getElementById('modal-basic-details');
    if (!modal) return;
    modal.classList.remove('hidden');

    this.modalSelectGender(this.state.patient.gender);
    document.getElementById('modal-age-range').value = this.state.patient.age;
    document.getElementById('modal-age-display').textContent = `${this.state.patient.age} years`;
    document.getElementById('modal-weight-range').value = this.state.patient.weight;
    document.getElementById('modal-weight-display').textContent = `${this.state.patient.weight} kg`;
  }

  modalSelectGender(gender) {
    this.tempModalGender = gender;
    ['female', 'male', 'other'].forEach(g => {
      const btn = document.getElementById(`modal-gender-${g}`);
      if (btn) btn.classList.toggle('active', g === gender);
    });
  }

  modalOnAgeChange(val) {
    document.getElementById('modal-age-display').textContent = `${val} years`;
  }

  modalOnWeightChange(val) {
    document.getElementById('modal-weight-display').textContent = `${val} kg`;
  }

  saveBasicDetailsModal() {
    if (this.tempModalGender) {
      this.setGender(this.tempModalGender);
    }
    const ageVal = parseInt(document.getElementById('modal-age-range').value, 10);
    const weightVal = parseFloat(document.getElementById('modal-weight-range').value);

    this.state.patient.age = ageVal;
    this.state.patient.weight = weightVal;
    this.updateSidebarDemographics();
    this.closeBasicDetailsModal();
  }

  closeBasicDetailsModal() {
    const modal = document.getElementById('modal-basic-details');
    if (modal) modal.classList.add('hidden');
  }

  // -------------------------------------------------------------------------
  // Info Modals (About, How it works, Disclaimer, Health Tips)
  // -------------------------------------------------------------------------
  showInfoModal(type) {
    const modal = document.getElementById('modal-info');
    const title = document.getElementById('info-modal-title');
    const content = document.getElementById('info-modal-content');
    if (!modal || !title || !content) return;

    if (type === 'about') {
      title.textContent = 'About QuickDiagnosis';
      content.innerHTML = `
        <p style="margin-bottom: 0.75rem;"><strong>QuickDiagnosis</strong> is an intelligent medical preliminary health screening tool built with Python OOP, data structures, Flask, and modern web standards.</p>
        <p style="color: var(--text-muted); line-height: 1.6;">Our mission is to help people understand their health symptoms early and calmly, offering evidence-based medical education and actionable care measurements.</p>
      `;
    } else if (type === 'how') {
      title.textContent = 'How QuickDiagnosis Works';
      content.innerHTML = `
        <div style="display: flex; flex-direction: column; gap: 0.75rem; color: var(--text-muted); line-height: 1.5;">
          <p><strong>1. Profile Calibration:</strong> Your biological gender, age, and weight tune disease risk prevalence curves.</p>
          <p><strong>2. Anatomical Selection:</strong> Explore the faceless medical body to pinpoint symptoms by system or search through the general catalog.</p>
          <p><strong>3. Probabilistic Evaluation:</strong> Our Python diagnostic engine calculates symptom similarity and presents the top 4–5 probable conditions with actionable curing measures.</p>
        </div>
      `;
    } else if (type === 'disclaimer') {
      title.textContent = 'Medical Disclaimer';
      content.innerHTML = `
        <p style="color: var(--text-muted); line-height: 1.6;">
          QuickDiagnosis is strictly an informational and educational screening application. It does NOT provide formal medical diagnoses or prescriptions. 
          If you are experiencing severe, worsening, or emergency symptoms, please contact emergency medical services or visit your nearest medical clinic immediately.
        </p>
      `;
    }

    modal.classList.remove('hidden');
  }

  showHealthTipsModal() {
    const modal = document.getElementById('modal-info');
    const title = document.getElementById('info-modal-title');
    const content = document.getElementById('info-modal-content');
    if (!modal || !title || !content) return;

    title.textContent = 'Daily Health & Vitality Tips';
    content.innerHTML = `
      <ul style="list-style: none; display: flex; flex-direction: column; gap: 0.75rem; color: var(--text-muted); line-height: 1.5;">
        <li>💧 <strong>Hydration:</strong> Drink at least 2.5 liters of clean water daily to assist renal filtration and lymphatic circulation.</li>
        <li>🛌 <strong>Restful Sleep:</strong> Aim for 7–8 hours of consistent sleep to allow cellular immune repair.</li>
        <li>🚶 <strong>Daily Movement:</strong> A 20-minute daily walk improves metabolic sensitivity and cardiovascular tone.</li>
        <li>🧠 <strong>Stress Relief:</strong> 5 minutes of deep diaphragmatic breathing stimulates vagus nerve relaxation.</li>
      </ul>
    `;
    modal.classList.remove('hidden');
  }

  closeInfoModal() {
    const modal = document.getElementById('modal-info');
    if (modal) modal.classList.add('hidden');
  }

  // -------------------------------------------------------------------------
  // CLINICAL LABORATORY MODULE (FastAPI & Deterministic OOP Engine)
  // -------------------------------------------------------------------------
  async loadLabDefinitions() {
    try {
      const res = await fetch('/api/lab-reports/definitions');
      const data = await res.json();
      if (data.success && data.definitions) {
        this.state.labDefinitions = data.definitions;
        const datalist = document.getElementById('supported-tests-datalist');
        if (datalist) {
          datalist.innerHTML = data.definitions.map(d => `<option value="${d.test_name}">${d.category || ''} (${d.unit || ''})</option>`).join('');
        }
      }
    } catch (e) {
      console.warn('Could not load lab definitions:', e);
    }
  }

  async loadLabReports() {
    try {
      const res = await fetch('/api/lab-reports');
      const data = await res.json();
      if (data.success && data.reports) {
        this.state.labReports = data.reports;
        this.updateLabReportsUI();
      }
    } catch (e) {
      console.warn('Could not load lab reports:', e);
    }
  }

  updateLabReportsUI() {
    const reports = this.state.labReports || [];
    
    // Update badge in tab
    const tabBadge = document.getElementById('lab-history-count-badge');
    if (tabBadge) tabBadge.textContent = reports.length;

    // Update stats
    const statTotalReps = document.getElementById('stat-total-reports');
    const statTotalTests = document.getElementById('stat-total-tests');
    const statAbnormal = document.getElementById('stat-abnormal-tests');
    const statLatestDate = document.getElementById('stat-latest-date');

    let totalTests = 0;
    let totalAbnormal = 0;
    reports.forEach(r => {
      totalTests += (r.total_tests || (r.tests ? r.tests.length : 0));
      totalAbnormal += (r.abnormal_tests_count || 0);
    });

    if (statTotalReps) statTotalReps.textContent = reports.length;
    if (statTotalTests) statTotalTests.textContent = totalTests;
    if (statAbnormal) statAbnormal.textContent = totalAbnormal;
    if (statLatestDate) statLatestDate.textContent = reports.length > 0 ? reports[0].report_date : '—';

    // Update screening drawer dropdown
    const selectEl = document.getElementById('diagnosis-lab-report-select');
    if (selectEl) {
      const currentVal = selectEl.value;
      selectEl.innerHTML = '<option value="">-- No Lab Report Attached (Symptom-Only Check) --</option>';
      reports.forEach(r => {
        const opt = document.createElement('option');
        opt.value = r.report_id;
        opt.textContent = `${r.report_date} - ${r.notes || 'Lab Panel'} (${r.abnormal_tests_count || 0} abnormal)`;
        selectEl.appendChild(opt);
      });
      if (currentVal && reports.some(r => r.report_id === currentVal)) {
        selectEl.value = currentVal;
      }
    }

    // Render history grid
    this.renderLabReportsHistory();
  }

  switchLabTab(tabName) {
    this.state.activeLabTab = tabName;
    ['history', 'add', 'trends'].forEach(t => {
      const btn = document.getElementById(`lab-tab-btn-${t}`);
      const content = document.getElementById(`lab-tab-content-${t}`);
      if (btn) btn.classList.toggle('active', t === tabName);
      if (content) content.classList.toggle('hidden', t !== tabName);
    });

    if (tabName === 'trends') {
      this.loadLabTrends();
    } else if (tabName === 'add' && this.state.manualTestRowCount === 0) {
      // Seed initial sample test rows in manual form
      this.initSampleManualRows();
    }
  }

  setAddReportMode(mode) {
    this.state.addReportMode = mode;
    const btnFile = document.getElementById('mode-btn-file');
    const btnManual = document.getElementById('mode-btn-manual');
    const contFile = document.getElementById('lab-mode-file');
    const contManual = document.getElementById('lab-mode-manual');

    if (btnFile) btnFile.classList.toggle('active', mode === 'file');
    if (btnManual) btnManual.classList.toggle('active', mode === 'manual');
    if (contFile) contFile.classList.toggle('hidden', mode !== 'file');
    if (contManual) contManual.classList.toggle('hidden', mode !== 'manual');

    if (mode === 'manual' && this.state.manualTestRowCount === 0) {
      this.initSampleManualRows();
    }
  }

  renderLabReportsHistory() {
    const grid = document.getElementById('lab-reports-grid');
    if (!grid) return;
    grid.innerHTML = '';

    const reports = this.state.labReports || [];
    if (reports.length === 0) {
      grid.innerHTML = `
        <div class="empty-reports-card">
          <div class="empty-icon">🧪</div>
          <h3>No Laboratory Reports Saved Yet</h3>
          <p>Upload a CSV/JSON blood report or manually enter laboratory values to correlate clinical findings.</p>
          <button class="btn btn-hero-cta" onclick="app.switchLabTab('add')">
            <span>+ Add or Upload Report</span>
          </button>
        </div>
      `;
      return;
    }

    reports.forEach(r => {
      const card = document.createElement('div');
      card.className = 'lab-report-card';

      // Gather preview of tests
      const tests = r.tests || [];
      const abnormalList = tests.filter(t => t.status === 'LOW' || t.status === 'HIGH');
      const normalList = tests.filter(t => t.status === 'NORMAL');

      const abnormalPills = abnormalList.slice(0, 4).map(t => `
        <span class="report-test-pill pill-${t.status.toLowerCase()}">
          <strong>${t.test_name}</strong> ${t.value} ${t.unit} [${t.status}]
        </span>
      `).join(' ');

      const isAttached = this.state.attachedLabReportId === r.report_id;

      card.innerHTML = `
        <div class="report-card-top">
          <div class="report-date-badge">
            <span class="date-icon">📅</span>
            <strong>${r.report_date}</strong>
          </div>
          <div class="report-counts-badge">
            <span>${tests.length} Biomarkers</span>
            ${abnormalList.length > 0 ? `<span class="abnormal-flag-badge">⚠️ ${abnormalList.length} Abnormal</span>` : '<span class="normal-flag-badge">✓ All Normal</span>'}
          </div>
        </div>

        <h3 class="report-title">${r.notes || 'Routine Diagnostic Blood Panel'}</h3>
        <div class="report-patient-meta">Patient: <strong>${r.patient_id || 'P_CURRENT'}</strong> • Created: ${r.created_at ? r.created_at.slice(0, 10) : r.report_date}</div>

        <div class="report-tests-preview">
          ${abnormalPills ? `
            <div class="preview-group">
              <span class="preview-label">Abnormal Findings:</span>
              <div class="preview-pills-row">${abnormalPills}</div>
            </div>
          ` : `
            <div class="preview-group">
              <span class="preview-label">Findings:</span>
              <span class="preview-normal-note">All measured biomarkers within reference ranges.</span>
            </div>
          `}
        </div>

        <div class="report-card-actions">
          <div class="actions-left">
            <button class="btn-micro-chip" onclick="app.openLabDetailModal('${r.report_id}')">👁️ View Tests</button>
            <button class="btn-micro-chip" onclick="app.exportCurrentModalReport('json', '${r.report_id}')">📥 JSON</button>
            <button class="btn-micro-chip" onclick="app.exportCurrentModalReport('csv', '${r.report_id}')">📊 CSV</button>
          </div>
          <div class="actions-right">
            ${isAttached ? `
              <span class="attached-active-chip">✓ Attached to Screening</span>
            ` : `
              <button class="btn-use-screening" onclick="app.screenWithReport('${r.report_id}')">
                <span>⚡ Use in Diagnosis</span>
              </button>
            `}
          </div>
        </div>
      `;

      grid.appendChild(card);
    });
  }

  async loadLabTrends() {
    const container = document.getElementById('trends-container');
    if (!container) return;
    container.innerHTML = '<div style="padding: 2rem; text-align: center; color: var(--text-muted);">Calculating deterministic biomarker trends...</div>';

    try {
      const res = await fetch('/api/lab-reports/trends');
      const data = await res.json();
      
      if (!data.success || !data.data || !data.data.has_sufficient_history) {
        container.innerHTML = `
          <div class="empty-reports-card">
            <div class="empty-icon">📈</div>
            <h3>Insufficient History For Trends</h3>
            <p>${data.data && data.data.message ? data.data.message : 'Please add at least 2 chronological lab reports to calculate deterministic biomarker trends over time.'}</p>
            <button class="btn btn-hero-cta" onclick="app.switchLabTab('add')">
              <span>+ Add Second Report</span>
            </button>
          </div>
        `;
        return;
      }

      const trendData = data.data;
      const trends = trendData.trends || [];

      let rowsHtml = '';
      trends.forEach(t => {
        const deltaFormatted = (t.delta > 0 ? `+${t.delta}` : `${t.delta}`) + ` ${t.unit}`;
        const pctFormatted = (t.pct_change > 0 ? `+${t.pct_change}%` : `${t.pct_change}%`);

        rowsHtml += `
          <tr class="trend-row dir-${t.direction.toLowerCase()}">
            <td class="trend-test-cell">
              <strong>${t.test_name}</strong>
              <div class="ref-sub-note">Range: ${t.reference_low !== null ? t.reference_low : '—'} - ${t.reference_high !== null ? t.reference_high : '—'} ${t.unit}</div>
            </td>
            <td>
              <div class="trend-reading-box">
                <span class="reading-val">${t.previous_value} ${t.unit}</span>
                <span class="status-pill status-${t.previous_status.toLowerCase()}">${t.previous_status}</span>
                <span class="reading-date">${t.previous_date}</span>
              </div>
            </td>
            <td>
              <div class="trend-reading-box">
                <strong class="reading-val-bold">${t.latest_value} ${t.unit}</strong>
                <span class="status-pill status-${t.latest_status.toLowerCase()}">${t.latest_status}</span>
                <span class="reading-date">${t.latest_date}</span>
              </div>
            </td>
            <td>
              <div class="trend-change-box">
                <strong class="trend-delta">${deltaFormatted}</strong>
                <span class="trend-pct">${pctFormatted}</span>
              </div>
            </td>
            <td>
              <span class="trend-pill pill-${t.direction.toLowerCase()}">
                <span>${t.icon}</span>
                <span>${t.direction}</span>
              </span>
            </td>
          </tr>
        `;
      });

      container.innerHTML = `
        <div class="trends-summary-header">
          <div>
            <h3 class="trends-title">Longitudinal Biomarker Trajectory</h3>
            <p class="trends-desc">Analyzed ${trendData.analyzed_tests_count} biomarkers across ${trendData.total_reports} panels (${trendData.earliest_report_date} to ${trendData.latest_report_date}).</p>
          </div>
          <button class="btn btn-secondary-outline" onclick="app.loadLabTrends()">🔄 Refresh Trends</button>
        </div>

        <div class="trends-table-wrap">
          <table class="trends-table">
            <thead>
              <tr>
                <th style="width: 28%;">Biomarker &amp; Range</th>
                <th style="width: 20%;">Previous Result</th>
                <th style="width: 20%;">Latest Result</th>
                <th style="width: 16%;">Absolute &amp; % Delta</th>
                <th style="width: 16%;">Deterministic Trend</th>
              </tr>
            </thead>
            <tbody>
              ${rowsHtml}
            </tbody>
          </table>
        </div>
      `;
    } catch (e) {
      console.error('Error loading trends:', e);
      container.innerHTML = '<div style="padding: 2rem; text-align: center; color: var(--accent-danger);">Could not calculate trends. Please check backend connection.</div>';
    }
  }

  // -------------------------------------------------------------------------
  // Report Detail Modal Handlers
  // -------------------------------------------------------------------------
  openLabDetailModal(reportId) {
    const report = (this.state.labReports || []).find(r => r.report_id === reportId);
    if (!report) return;

    this.state.currentModalReportId = reportId;
    const modal = document.getElementById('modal-lab-report-detail');
    if (!modal) return;

    const titleEl = document.getElementById('modal-lab-title');
    const dateEl = document.getElementById('modal-lab-date');
    const metaEl = document.getElementById('modal-lab-meta');
    const tbody = document.getElementById('modal-lab-tests-tbody');

    if (titleEl) titleEl.textContent = report.notes || 'Clinical Laboratory Panel';
    if (dateEl) dateEl.textContent = `Panel Date: ${report.report_date}`;

    const tests = report.tests || [];
    const abnormalCount = tests.filter(t => t.status === 'LOW' || t.status === 'HIGH').length;

    if (metaEl) {
      metaEl.innerHTML = `
        <div>Patient ID: <strong>${report.patient_id || 'P_CURRENT'}</strong></div>
        <div>Total Tests: <strong>${tests.length}</strong></div>
        <div>Abnormal Tests: <strong class="${abnormalCount > 0 ? 'accent-danger-text' : ''}">${abnormalCount}</strong></div>
        <div>Report ID: <code>${report.report_id}</code></div>
      `;
    }

    if (tbody) {
      tbody.innerHTML = tests.map(t => `
        <tr>
          <td><strong>${t.test_name}</strong></td>
          <td><strong class="test-val-bold">${t.value}</strong> <span class="test-unit">${t.unit}</span></td>
          <td>${t.reference_low !== null ? t.reference_low : '—'} - ${t.reference_high !== null ? t.reference_high : '—'} ${t.unit}</td>
          <td><span class="status-pill status-${t.status.toLowerCase()}">${t.status}</span></td>
        </tr>
      `).join('');
    }

    modal.classList.remove('hidden');
  }

  closeLabDetailModal() {
    const modal = document.getElementById('modal-lab-report-detail');
    if (modal) modal.classList.add('hidden');
    this.state.currentModalReportId = null;
  }

  async deleteCurrentModalReport() {
    const repId = this.state.currentModalReportId;
    if (!repId) return;

    if (!confirm('Are you sure you want to delete this laboratory report from your records?')) {
      return;
    }

    try {
      const res = await fetch(`/api/lab-reports/${repId}`, { method: 'DELETE' });
      const data = await res.json();
      if (data.success) {
        if (this.state.attachedLabReportId === repId) {
          this.state.attachedLabReportId = null;
          this.onLabReportSelected('');
        }
        await this.loadLabReports();
        this.closeLabDetailModal();
      } else {
        alert(data.detail || 'Could not delete report.');
      }
    } catch (e) {
      alert('Delete request failed: ' + e);
    }
  }

  exportCurrentModalReport(format, explicitId = null) {
    const repId = explicitId || this.state.currentModalReportId;
    if (!repId) return;
    window.open(`/api/lab-reports/${repId}/export?format=${format}`, '_blank');
  }

  screenWithCurrentModalReport() {
    const repId = this.state.currentModalReportId;
    if (!repId) return;
    this.screenWithReport(repId);
    this.closeLabDetailModal();
  }

  screenWithReport(reportId) {
    this.state.attachedLabReportId = reportId;
    const selectEl = document.getElementById('diagnosis-lab-report-select');
    if (selectEl) selectEl.value = reportId;
    this.onLabReportSelected(reportId);
    this.showDiagnosisView();
  }

  onLabReportSelected(reportId) {
    this.state.attachedLabReportId = reportId || null;
    const previewEl = document.getElementById('diagnosis-lab-report-summary');
    if (!previewEl) return;

    if (!reportId) {
      previewEl.classList.add('hidden');
      previewEl.innerHTML = '';
      return;
    }

    const report = (this.state.labReports || []).find(r => r.report_id === reportId);
    if (!report) {
      previewEl.classList.add('hidden');
      return;
    }

    const tests = report.tests || [];
    const abnormal = tests.filter(t => t.status === 'LOW' || t.status === 'HIGH');

    previewEl.classList.remove('hidden');
    previewEl.innerHTML = `
      <div class="attached-chip-inner">
        <span>🧪 Report Attached: <strong>${report.report_date}</strong></span>
        <span>•</span>
        <span>${tests.length} Biomarkers</span>
        <span>•</span>
        <span class="${abnormal.length > 0 ? 'abnormal-count-tag' : 'normal-count-tag'}">
          ${abnormal.length > 0 ? `${abnormal.length} abnormal values will corroborate screening` : 'All normal values'}
        </span>
        <button type="button" class="btn-chip-remove" onclick="app.onLabReportSelected(''); document.getElementById('diagnosis-lab-report-select').value='';" title="Detach">✕</button>
      </div>
    `;
  }

  // -------------------------------------------------------------------------
  // File Upload Handlers (Drag & Drop + Input)
  // -------------------------------------------------------------------------
  onFileDragOver(e) {
    e.preventDefault();
    const dropzone = document.getElementById('file-dropzone');
    if (dropzone) dropzone.classList.add('drag-active');
  }

  onFileDragLeave(e) {
    e.preventDefault();
    const dropzone = document.getElementById('file-dropzone');
    if (dropzone) dropzone.classList.remove('drag-active');
  }

  onFileDrop(e) {
    e.preventDefault();
    const dropzone = document.getElementById('file-dropzone');
    if (dropzone) dropzone.classList.remove('drag-active');
    
    if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      this.uploadLabFile(e.dataTransfer.files[0]);
    }
  }

  onFileSelected(input) {
    if (input && input.files && input.files.length > 0) {
      this.uploadLabFile(input.files[0]);
    }
  }

  async uploadLabFile(file) {
    const statusEl = document.getElementById('file-upload-status');
    if (statusEl) {
      statusEl.classList.remove('hidden');
      statusEl.className = 'file-upload-status-chip status-loading';
      statusEl.textContent = `Reading and parsing '${file.name}'...`;
    }

    const formData = new FormData();
    formData.append('file', file);
    formData.append('patient_id', 'P_CURRENT');

    try {
      const res = await fetch('/api/lab-reports/upload', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();

      if (res.ok && data.success) {
        if (statusEl) {
          statusEl.className = 'file-upload-status-chip status-success';
          statusEl.textContent = `✓ Success: ${data.message}`;
        }
        await this.loadLabReports();
        setTimeout(() => {
          this.switchLabTab('history');
          if (statusEl) statusEl.classList.add('hidden');
        }, 1200);
      } else {
        if (statusEl) {
          statusEl.className = 'file-upload-status-chip status-error';
          statusEl.textContent = `❌ ${data.detail || 'Failed to process file'}`;
        }
      }
    } catch (e) {
      if (statusEl) {
        statusEl.className = 'file-upload-status-chip status-error';
        statusEl.textContent = `❌ Upload failed: ${e.message}`;
      }
    }
  }

  // -------------------------------------------------------------------------
  // Manual Lab Entry Handlers
  // -------------------------------------------------------------------------
  initSampleManualRows() {
    const tbody = document.getElementById('manual-tests-tbody');
    if (!tbody) return;
    tbody.innerHTML = '';
    this.state.manualTestRowCount = 0;

    const dateInput = document.getElementById('manual-report-date');
    if (dateInput && !dateInput.value) {
      dateInput.value = new Date().toISOString().slice(0, 10);
    }

    // Pre-populate 4 standard screening markers
    this.addManualTestRow({ name: 'Hemoglobin', value: 13.5 });
    this.addManualTestRow({ name: 'Fasting Glucose', value: 92.0 });
    this.addManualTestRow({ name: 'HbA1c', value: 5.4 });
    this.addManualTestRow({ name: 'Vitamin D (25-OH)', value: 25.0 });
  }

  addManualTestRow(initData = {}) {
    const tbody = document.getElementById('manual-tests-tbody');
    if (!tbody) return;

    this.state.manualTestRowCount += 1;
    const rowId = `row_${Date.now()}_${this.state.manualTestRowCount}`;

    const defName = initData.name || '';
    const def = this.state.labDefinitions.find(d => d.test_name.toLowerCase() === defName.toLowerCase()) || {};

    const unitVal = initData.unit || def.unit || '';
    const lowVal = initData.reference_low !== undefined ? initData.reference_low : (def.reference_low !== undefined ? def.reference_low : '');
    const highVal = initData.reference_high !== undefined ? initData.reference_high : (def.reference_high !== undefined ? def.reference_high : '');
    const initialVal = initData.value !== undefined ? initData.value : '';

    const tr = document.createElement('tr');
    tr.id = rowId;
    tr.innerHTML = `
      <td>
        <input type="text" list="supported-tests-datalist" class="styled-table-input test-name-input" value="${defName}" placeholder="Select or type test name" onchange="app.onManualTestNameChange('${rowId}', this.value)" required>
      </td>
      <td>
        <input type="number" step="any" class="styled-table-input test-val-input" value="${initialVal}" placeholder="e.g. 12.5" oninput="app.onManualTestChange('${rowId}')" required>
      </td>
      <td>
        <input type="text" class="styled-table-input test-unit-input" value="${unitVal}" placeholder="Unit">
      </td>
      <td>
        <input type="number" step="any" class="styled-table-input test-low-input" value="${lowVal}" placeholder="Low" oninput="app.onManualTestChange('${rowId}')">
      </td>
      <td>
        <input type="number" step="any" class="styled-table-input test-high-input" value="${highVal}" placeholder="High" oninput="app.onManualTestChange('${rowId}')">
      </td>
      <td>
        <span class="status-pill status-unknown status-pill-badge" id="${rowId}_status">UNKNOWN</span>
      </td>
      <td>
        <button type="button" class="btn-row-del" onclick="app.removeManualTestRow('${rowId}')" title="Remove row">✕</button>
      </td>
    `;

    tbody.appendChild(tr);
    this.onManualTestChange(rowId);
  }

  onManualTestNameChange(rowId, val) {
    if (!val) return;
    const def = this.state.labDefinitions.find(d => d.test_name.toLowerCase() === val.trim().toLowerCase());
    if (def) {
      const tr = document.getElementById(rowId);
      if (!tr) return;
      const unitInput = tr.querySelector('.test-unit-input');
      const lowInput = tr.querySelector('.test-low-input');
      const highInput = tr.querySelector('.test-high-input');

      if (unitInput && def.unit) unitInput.value = def.unit;
      if (lowInput && def.reference_low !== undefined) lowInput.value = def.reference_low;
      if (highInput && def.reference_high !== undefined) highInput.value = def.reference_high;
      this.onManualTestChange(rowId);
    }
  }

  onManualTestChange(rowId) {
    const tr = document.getElementById(rowId);
    if (!tr) return;

    const valStr = tr.querySelector('.test-val-input').value;
    const lowStr = tr.querySelector('.test-low-input').value;
    const highStr = tr.querySelector('.test-high-input').value;
    const statusBadge = document.getElementById(`${rowId}_status`);
    if (!statusBadge) return;

    if (valStr === '' || isNaN(parseFloat(valStr))) {
      statusBadge.textContent = 'UNKNOWN';
      statusBadge.className = 'status-pill status-unknown status-pill-badge';
      return;
    }

    const val = parseFloat(valStr);
    const low = lowStr !== '' && !isNaN(parseFloat(lowStr)) ? parseFloat(lowStr) : null;
    const high = highStr !== '' && !isNaN(parseFloat(highStr)) ? parseFloat(highStr) : null;

    let status = 'UNKNOWN';
    if (low !== null && high !== null) {
      if (val < low) status = 'LOW';
      else if (val > high) status = 'HIGH';
      else status = 'NORMAL';
    } else if (high !== null) {
      status = val > high ? 'HIGH' : 'NORMAL';
    } else if (low !== null) {
      status = val < low ? 'LOW' : 'NORMAL';
    }

    statusBadge.textContent = status;
    statusBadge.className = `status-pill status-${status.toLowerCase()} status-pill-badge`;
  }

  removeManualTestRow(rowId) {
    const tr = document.getElementById(rowId);
    if (tr) tr.remove();
  }

  resetManualForm() {
    this.initSampleManualRows();
  }

  async submitManualLabReport(event) {
    event.preventDefault();
    const dateInput = document.getElementById('manual-report-date');
    const patientInput = document.getElementById('manual-patient-id');
    const notesInput = document.getElementById('manual-report-notes');
    const tbody = document.getElementById('manual-tests-tbody');

    const dateVal = dateInput ? dateInput.value : '';
    const patientVal = patientInput && patientInput.value ? patientInput.value.trim() : 'P_CURRENT';
    const notesVal = notesInput ? notesInput.value.trim() : '';

    const rows = tbody ? Array.from(tbody.querySelectorAll('tr')) : [];
    if (rows.length === 0) {
      alert('Please add at least 1 laboratory test to save the report.');
      return;
    }

    const tests = [];
    for (const r of rows) {
      const name = r.querySelector('.test-name-input').value.trim();
      const valStr = r.querySelector('.test-val-input').value.trim();
      const unit = r.querySelector('.test-unit-input').value.trim();
      const lowStr = r.querySelector('.test-low-input').value.trim();
      const highStr = r.querySelector('.test-high-input').value.trim();

      if (!name || valStr === '') continue;

      const val = parseFloat(valStr);
      const low = lowStr !== '' ? parseFloat(lowStr) : null;
      const high = highStr !== '' ? parseFloat(highStr) : null;

      tests.push({
        test_name: name,
        value: val,
        unit: unit,
        reference_low: low,
        reference_high: high
      });
    }

    if (tests.length === 0) {
      alert('Please ensure all tests have valid names and numeric values.');
      return;
    }

    const payload = {
      patient_id: patientVal,
      report_date: dateVal,
      notes: notesVal || 'Manual Clinical Panel',
      tests: tests
    };

    try {
      const res = await fetch('/api/lab-reports', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();

      if (res.ok && data.success) {
        await this.loadLabReports();
        this.switchLabTab('history');
      } else {
        alert(data.detail || 'Could not save report.');
      }
    } catch (e) {
      alert('Save request failed: ' + e);
    }
  }

  downloadSampleCSV() {
    const csvContent = "test_name,value,unit,reference_low,reference_high\nHemoglobin,10.8,g/dL,12.0,17.5\nFerritin,11.0,ng/mL,20.0,250.0\nFasting Glucose,95.0,mg/dL,70.0,99.0\nHbA1c,5.5,%,4.0,5.6\nVitamin D,28.0,ng/mL,30.0,100.0\nTSH,2.3,uIU/mL,0.4,4.0\nSerum Sodium,140.0,mEq/L,135.0,145.0\nSerum Potassium,4.2,mEq/L,3.5,5.0\n";
    this._triggerClientDownload(csvContent, "sample_lab_report.csv", "text/csv");
  }

  downloadSampleJSON() {
    const jsonObj = {
      "patient_id": "P_SAMPLE",
      "report_date": new Date().toISOString().slice(0, 10),
      "notes": "Sample Laboratory Blood Panel",
      "tests": [
        { "test_name": "Hemoglobin", "value": 10.8, "unit": "g/dL", "reference_low": 12.0, "reference_high": 17.5 },
        { "test_name": "Ferritin", "value": 11.0, "unit": "ng/mL", "reference_low": 20.0, "reference_high": 250.0 },
        { "test_name": "Fasting Glucose", "value": 95.0, "unit": "mg/dL", "reference_low": 70.0, "reference_high": 99.0 },
        { "test_name": "HbA1c", "value": 5.5, "unit": "%", "reference_low": 4.0, "reference_high": 5.6 },
        { "test_name": "Vitamin D (25-OH)", "value": 28.0, "unit": "ng/mL", "reference_low": 30.0, "reference_high": 100.0 }
      ]
    };
    this._triggerClientDownload(JSON.stringify(jsonObj, null, 2), "sample_lab_report.json", "application/json");
  }

  _triggerClientDownload(content, filename, mimeType) {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }
}

// Global App Instance
const app = new QuickDiagnosisApp();
document.addEventListener('DOMContentLoaded', () => {
  app.init();
});
