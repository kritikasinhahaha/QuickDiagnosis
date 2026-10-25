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
      deferredPwaPrompt: null
    };

    // DOM Views
    this.views = {
      welcome: document.getElementById('view-welcome'),
      step1: document.getElementById('view-step1'),
      diagnosis: document.getElementById('view-diagnosis'),
      results: document.getElementById('view-results')
    };
  }

  async init() {
    this.applyTheme(this.state.theme);
    this.initPwa();
    this.initUserName();
    await this.loadConfig();
    await this.loadSymptoms();
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
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  showStep1View() {
    this.views.welcome.classList.add('hidden');
    if (this.views.step1) this.views.step1.classList.remove('hidden');
    this.views.diagnosis.classList.add('hidden');
    this.views.results.classList.add('hidden');
    this.syncStep1Controls();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  showDiagnosisView() {
    this.views.welcome.classList.add('hidden');
    if (this.views.step1) this.views.step1.classList.add('hidden');
    this.views.diagnosis.classList.remove('hidden');
    this.views.results.classList.add('hidden');
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
    window.scrollTo({ top: 0, behavior: 'smooth' });
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
        symptoms: Array.from(this.state.selectedSymptoms)
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
      summaryEl.textContent = `Screening for: ${g}, ${this.state.patient.age} years, ${this.state.patient.weight} kg • ${data.selected_symptoms_count} symptoms reported`;
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

        ${dis.risk_explanation ? `
          <div style="background: rgba(37,99,235,0.08); border-left: 3px solid #2563eb; padding: 0.6rem 0.85rem; border-radius: 0 8px 8px 0; font-size: 0.8rem; color: var(--text-main);">
            <strong>Demographic Factor:</strong> ${dis.risk_explanation}
          </div>
        ` : ''}

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
    } catch (err) {
      console.error('Error fetching disease:', err);
    }
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
}

// Global App Instance
const app = new QuickDiagnosisApp();
document.addEventListener('DOMContentLoaded', () => {
  app.init();
});
