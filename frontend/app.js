// JavaScript Application for Antigravity Health Ops Portal

const API_BASE = ""; // Local relative API paths

// Global Application State
let patients = [];
let selectedPatientId = null;
let currentTab = "journey";
let selectedPatientForAgent = null;
let pendingPatients = {};

// Tab Definitions for Header Titles
const TAB_HEADERS = {
    journey: { title: "Flujo del Paciente y Máquina de Estados", desc: "Monitorea, valida y simula transiciones clínicas bajo reglas estrictas" },
    coworker: { title: "Consola de Operaciones del Copiloto IA", desc: "Monitorea agentes clínicos, contexto de memoria y bucles de validación" },
    interop: { title: "Canalización de Datos e Ingesta Clínica", desc: "Ingiere feeds HL7 y traduce recursos al formato FHIR" },
    audit: { title: "Libro de Transacciones HIPAA", desc: "Inspecciona accesos PHI auditables y cambios de estado médico" },
    blueprint: { title: "Arquitectura del Sistema de Producción", desc: "Explora escalabilidad, invariantes y especificaciones de cumplimiento de datos" }
};

document.addEventListener("DOMContentLoaded", () => {
    initTabs();
    loadPatients();
    loadAuditTrail();
    setupEventHandlers();
    initTilt();
    initOrbParallax();
    runTabEntryAnimation(currentTab);
});

// 1. Navigation and Tab Switching
function initTabs() {
    const navButtons = document.querySelectorAll(".nav-btn");
    const tabPanes = document.querySelectorAll(".tab-pane");

    navButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetTab = btn.getAttribute("data-tab");
            
            // Toggle active classes
            navButtons.forEach(b => b.classList.remove("active"));
            tabPanes.forEach(pane => pane.classList.remove("active"));

            btn.classList.add("active");
            document.getElementById(`tab-${targetTab}`).classList.add("active");

            // Update page headers
            currentTab = targetTab;
            const headerInfo = TAB_HEADERS[targetTab];
            if (headerInfo) {
                document.getElementById("page-heading").innerText = headerInfo.title;
                document.getElementById("page-subheading").innerText = headerInfo.desc;
            }

            // Tab-specific loading actions
            if (targetTab === "audit") {
                loadAuditTrail();
            } else if (targetTab === "journey") {
                loadPatients(selectedPatientId); // Refresh selected patient
            }

            // Trigger entry animation for new tab cards
            runTabEntryAnimation(targetTab);
        });
    });
}

// 2. Fetch and Load Patients
async function loadPatients(selectId = null) {
    const listContainer = document.getElementById("patient-list-container");
    
    try {
        const response = await fetch(`${API_BASE}/api/patients`);
        patients = await response.json();
        
        listContainer.innerHTML = "";
        
        if (patients.length === 0) {
            listContainer.innerHTML = `<div class="loading-spinner">No hay pacientes registrados.</div>`;
            return;
        }

        patients.forEach(patient => {
            const card = document.createElement("div");
            card.className = `patient-card ${patient.id === selectId ? 'selected' : ''}`;
            card.onclick = () => selectPatient(patient.id);

            const stateClassMap = {
                "Admisión": "intake",
                "Evaluación Clínica": "evaluation",
                "Planificación de Tratamiento": "planning",
                "Terapia Activa": "therapy",
                "Intervención de Crisis": "crisis",
                "Alta Médica": "discharged"
            };
            const dotClass = stateClassMap[patient.current_state] || "intake";

            card.innerHTML = `
                <div class="patient-card-header">
                    <span class="patient-card-name">${patient.name}</span>
                    <span class="risk-tag ${patient.risk_level.toLowerCase()}">${patient.risk_level}</span>
                </div>
                <div class="patient-card-state">
                    <span class="state-dot ${dotClass}"></span>
                    <span>${patient.current_state}</span>
                </div>
            `;
            listContainer.appendChild(card);
        });

        // Set default selection if none
        if (patients.length > 0) {
            if (selectId && patients.some(p => p.id === selectId)) {
                selectPatient(selectId);
            } else {
                selectPatient(patients[0].id);
            }
        }
    } catch (err) {
        console.error("Error fetching patients:", err);
        listContainer.innerHTML = `<div class="loading-spinner" style="color:#f43f5e;">Error al cargar los pacientes.</div>`;
    }
}

// 3. Selection Focus Patient
function selectPatient(patientId) {
    selectedPatientId = patientId;
    
    // Highlight list selection
    const cards = document.querySelectorAll(".patient-card");
    cards.forEach(card => card.classList.remove("selected"));
    
    const activeIndex = patients.findIndex(p => p.id === patientId);
    if (activeIndex === -1) return;
    
    // Mark card as selected in UI list
    const patientCards = document.querySelectorAll(".patient-card");
    if (patientCards[activeIndex]) {
        patientCards[activeIndex].classList.add("selected");
    }

    const patient = patients[activeIndex];
    
    // Populate Focus Info
    document.getElementById("focus-patient-name").innerText = patient.name;
    document.getElementById("focus-patient-dob").innerText = patient.birthdate;
    document.getElementById("focus-patient-id").innerText = patient.id;
    
    // Risk Indicators
    const riskBadge = document.getElementById("focus-patient-risk");
    riskBadge.innerText = `Riesgo ${patient.risk_level}`;
    riskBadge.className = `risk-indicator risk-tag ${patient.risk_level.toLowerCase()}`;

    // Condition Tags
    const tagsContainer = document.getElementById("focus-patient-conditions");
    tagsContainer.innerHTML = "";
    if (patient.conditions && patient.conditions.length > 0) {
        patient.conditions.forEach(cond => {
            const tag = document.createElement("span");
            tag.className = "condition-tag";
            tag.innerHTML = `<code>${cond.code}</code> ${cond.display} (${cond.severity})`;
            tagsContainer.appendChild(tag);
        });
    } else {
        tagsContainer.innerHTML = `<span class="empty-tag">No hay diagnósticos clínicos registrados</span>`;
    }

    // Hide the override container
    document.getElementById("override-container").classList.add("hidden");
    document.getElementById("override-reason").value = "";
    document.getElementById("report-clinical-notes").value = "";

    // Sync transition button state
    const transitionBtn = document.getElementById("btn-trigger-transition");
    if (pendingPatients[patientId]) {
        transitionBtn.innerText = "Pendiente por Validación";
        transitionBtn.classList.add("btn-pending");
        transitionBtn.disabled = true;
    } else {
        transitionBtn.innerText = "Solicitar Cambio de Estado";
        transitionBtn.classList.remove("btn-pending");
        transitionBtn.disabled = false;
    }

    // Sync State timeline machine
    updateTimelineVisuals(patient.current_state);

    // Invariant rule text updater
    const invariantLabel = document.getElementById("invariant-rule-text");
    if (patient.risk_level === "Crítico") {
        invariantLabel.innerText = "INVARIANTE DE RIESGO CRÍTICO: El paciente debe permanecer en Intervención de Crisis. Las transiciones de salida están bloqueadas sin Autorización Médica.";
    } else if (patient.current_state === "Admisión") {
        invariantLabel.innerText = "INVARIANTE DE FLUJO: Las transiciones permitidas son 'Evaluación Clínica' o 'Intervención de Crisis'. El paso directo a Terapia está bloqueado.";
    } else {
        invariantLabel.innerText = "INVARIANTE ESTÁNDAR: Las transiciones deben seguir la secuencia. El Alta Médica está bloqueada si el riesgo es Alto o Crítico.";
    }
}

// 4. Update the Timeline UI elements
function updateTimelineVisuals(currentState) {
    const statesOrder = [
        "Admisión",
        "Evaluación Clínica",
        "Planificación de Tratamiento",
        "Terapia Activa",
        "Intervención de Crisis",
        "Alta Médica"
    ];

    const currentIdx = statesOrder.indexOf(currentState);
    const nodes = document.querySelectorAll(".state-node");

    nodes.forEach(node => {
        const nodeState = node.getAttribute("data-state");
        const nodeIdx = statesOrder.indexOf(nodeState);

        node.classList.remove("active", "completed");

        if (nodeState === currentState) {
            node.classList.add("active");
        } else if (nodeIdx < currentIdx && nodeState !== "Intervención de Crisis") {
            // Crisis intervention is not part of linear sequence, only color complete linear predecessors
            node.classList.add("completed");
        }
    });
}

// 5. Ingestion UI Handlers
function updateFHIRPreview(hl7Text) {
    const lines = hl7Text.trim().split("\n");
    let name = "Luke Skywalker";
    let dob = "1977-05-25";
    let conditions = [];

    lines.forEach(l => {
        const parts = l.split("|");
        if (parts[0] === "PID") {
            const names = parts[5] ? parts[5].split("^") : [];
            name = `${names[1] || ''} ${names[0] || ''}`.trim() || name;
            dob = parts[7] || dob;
            if (dob.length === 8) {
                dob = `${dob.substring(0,4)}-${dob.substring(4,6)}-${dob.substring(6,8)}`;
            }
        } else if (parts[0] === "OBX") {
            const codeParts = parts[3] ? parts[3].split("^") : [];
            conditions.push({
                code: codeParts[0] || "UNK",
                display: codeParts[1] || "Clinical Observation",
                severity: parts[8] === "H" ? "High" : "Low"
            });
        }
    });

    const mockFhir = {
        resourceType: "Patient",
        id: "PAT-004",
        name: [{ use: "official", text: name }],
        gender: "male",
        birthDate: dob,
        contained: conditions.map(c => ({
            resourceType: "Observation",
            code: { coding: [{ code: c.code, display: c.display }] },
            interpretation: [{ text: c.severity }]
        }))
    };

    document.getElementById("hl7-segment-preview").innerText = lines.find(l => l.startsWith("PID")) || "PID Segment Empty";
    document.getElementById("fhir-json-preview").innerText = JSON.stringify(mockFhir, null, 2);
}

// 6. Hook Event Handlers
function setupEventHandlers() {
    // State machine updates
    document.getElementById("btn-trigger-transition").addEventListener("click", () => triggerTransitionFlow(false));
    document.getElementById("btn-submit-override").addEventListener("click", () => triggerTransitionFlow(true));
    document.getElementById("btn-cancel-override").addEventListener("click", () => {
        document.getElementById("override-container").classList.add("hidden");
    });

    // Ingestions
    const hl7Input = document.getElementById("raw-hl7-input");
    hl7Input.addEventListener("input", () => updateFHIRPreview(hl7Input.value));
    updateFHIRPreview(hl7Input.value); // Initial preview run

    document.getElementById("btn-ingest-hl7").addEventListener("click", async () => {
        const rawHL7 = hl7Input.value;
        try {
            const res = await fetch(`${API_BASE}/api/interop/hl7`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ raw_message: rawHL7 })
            });
            const data = await res.json();
            if (data.status === "success") {
                alert(`¡Ingesta exitosa! Paciente '${data.patient.name}' cargado.`);
                loadPatients(data.patient.id);
            } else {
                alert("Error al ingerir mensaje HL7");
            }
        } catch (e) {
            console.error(e);
            alert("Error de conexión al ingerir HL7.");
        }
    });

    // AI Coworker Console
    document.getElementById("btn-fill-safe-note").addEventListener("click", () => {
        document.getElementById("agent-trigger-note").value = 
            "Paciente ingresado para observación de rutina. Notas: 'Me siento estable, dormí 7 horas anoche y estoy siguiendo los ejercicios de terapia.'";
    });

    document.getElementById("btn-run-agent").addEventListener("click", triggerAgentSimulation);

    // Export files
    document.getElementById("btn-export-html").addEventListener("click", () => {
        if (!selectedPatientId) return;
        const notes = encodeURIComponent(document.getElementById("report-clinical-notes").value);
        const pendingState = pendingPatients[selectedPatientId] ? encodeURIComponent(pendingPatients[selectedPatientId]) : '';
        window.open(`${API_BASE}/api/patients/${selectedPatientId}/export?format=html&notes=${notes}&pending_state=${pendingState}`, '_blank');
    });

    document.getElementById("btn-export-pdf").addEventListener("click", () => {
        if (!selectedPatientId) return;
        const notes = encodeURIComponent(document.getElementById("report-clinical-notes").value);
        const pendingState = pendingPatients[selectedPatientId] ? encodeURIComponent(pendingPatients[selectedPatientId]) : '';
        // Direct download file link
        window.location.href = `${API_BASE}/api/patients/${selectedPatientId}/export?format=pdf&notes=${notes}&pending_state=${pendingState}`;
    });

    // Audit logs
    document.getElementById("btn-refresh-audit").addEventListener("click", loadAuditTrail);
}

// 7. Transition engine trigger logic
async function triggerTransitionFlow(isOverride = false) {
    if (!selectedPatientId) {
        alert("Por favor, selecciona un paciente primero.");
        return;
    }
    
    const targetState = document.getElementById("transition-select").value;
    if (!targetState) {
        alert("Por favor, selecciona un estado objetivo.");
        return;
    }

    const payload = {
        patient_id: selectedPatientId,
        target_state: targetState,
        operator: "Dr. Evelyn Harper",
        reason: isOverride ? document.getElementById("override-reason").value : "",
        override: isOverride
    };

    if (isOverride && !payload.reason) {
        alert("Una justificación clínica es obligatoria para cumplir con las normas HIPAA.");
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/api/patients/transition`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            const data = await res.json();
            alert(`Transición a '${targetState}' procesada exitosamente.`);
            document.getElementById("override-container").classList.add("hidden");
            
            // Mark patient as pending validation with requested state
            pendingPatients[selectedPatientId] = targetState;
            
            // Update button immediately
            const transitionBtn = document.getElementById("btn-trigger-transition");
            transitionBtn.innerText = "Pendiente por Validación";
            transitionBtn.classList.add("btn-pending");
            transitionBtn.disabled = true;

            loadPatients(selectedPatientId);
        } else {
            const errData = await res.json();
            const detail = errData.detail;
            
            if (detail && detail.is_overrideable) {
                // Show override panel
                const overrideWarning = document.getElementById("override-warning-message");
                overrideWarning.innerText = detail.message;
                document.getElementById("override-container").classList.remove("hidden");
            } else {
                alert(`Error: ${detail ? detail.message || detail : "Acción denegada por los controles de seguridad clínicos."}`);
            }
        }
    } catch (e) {
        console.error(e);
        alert("Error al ejecutar la transición de estado.");
    }
}

// 8. Trigger AI Coworker simulation loop
async function triggerAgentSimulation() {
    if (!selectedPatientId) {
        alert("Selecciona un paciente en la pestaña 'Flujo del Paciente' primero.");
        return;
    }

    const consoleDiv = document.getElementById("agent-console");
    consoleDiv.innerHTML = `<div class="terminal-line system">[SISTEMA] Consultando estado para el Paciente ID: ${selectedPatientId}...</div>`;

    const noteText = document.getElementById("agent-trigger-note").value;

    try {
        const response = await fetch(`${API_BASE}/api/patients/${selectedPatientId}/agent-evaluate`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ note: noteText })
        });
        const trace = await response.json();

        // Print traces with delays to simulate the agent reasoning steps
        let index = 0;
        
        function printNextStep() {
            if (index === 0) {
                consoleDiv.innerHTML += `<div class="terminal-line system">[SISTEMA] Contexto de memoria cargado exitosamente. Elementos:</div>`;
                trace.memory_context_used.forEach(m => {
                    consoleDiv.innerHTML += `<div class="terminal-line" style="color: #64748b;">  ➔ "${m}"</div>`;
                });
            }

            if (index < trace.steps.length) {
                const step = trace.steps[index];
                consoleDiv.innerHTML += `
                    <div class="terminal-line system">[PASO DE FLUJO DE AGENTE ${index + 1}] Ejecutando Herramienta: <strong>${step.tool_name}</strong></div>
                    <div class="terminal-line tool"> &gt; Entrada: ${step.tool_input}</div>
                    <div class="terminal-line tool" style="color: #cbd5e1;"> &gt; Salida: ${step.tool_output}</div>
                `;
                index++;
                consoleDiv.scrollTop = consoleDiv.scrollHeight;
                setTimeout(printNextStep, 800);
            } else {
                // Done with steps, show safety evaluation details
                consoleDiv.innerHTML += `
                    <div class="terminal-line system">[SISTEMA] Ejecutando Controles de Auditoría de Seguridad...</div>
                    <div class="terminal-line safety ${trace.safety_checks_passed ? '' : 'failed'}">
                        [EVALUACIÓN DE SEGURIDAD] Verificado contra protocolos. Aprobado: ${trace.safety_checks_passed} | Reintentos: ${trace.retries_count}
                    </div>
                    <div class="terminal-line final">
                        [DECISIÓN FINAL / INSTRUCCIÓN DE ACCIÓN]
                        <br>${trace.final_decision}
                    </div>
                `;
                consoleDiv.scrollTop = consoleDiv.scrollHeight;
            }
        }
        
        setTimeout(printNextStep, 500);

    } catch (e) {
        consoleDiv.innerHTML += `<div class="terminal-line safety failed">[ERROR] Fallo al ejecutar el hilo del agente Copiloto IA. Revisa los logs del servidor.</div>`;
    }
}

// 9. Load Audit Ledger
async function loadAuditTrail() {
    const tbody = document.getElementById("audit-table-body");
    tbody.innerHTML = `<tr><td colspan="5" style="text-align: center;">Actualizando eventos del libro mayor...</td></tr>`;

    try {
        const res = await fetch(`${API_BASE}/api/audit-logs`);
        const logs = await res.json();
        
        tbody.innerHTML = "";
        
        if (logs.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-dark);">El libro de auditoría está vacío. Provoca transiciones de estado o ingiere archivos para generar registros.</td></tr>`;
            return;
        }

        // Sort descending by timestamp
        logs.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

        logs.forEach(log => {
            const tr = document.createElement("tr");
            
            const badgeClass = log.event_type.toLowerCase();
            const dateStr = new Date(log.timestamp).toLocaleString();

            tr.innerHTML = `
                <td style="color: var(--primary-teal); font-family: 'JetBrains Mono', monospace; font-size: 11px;">${dateStr}</td>
                <td><span class="audit-badge ${badgeClass}">${log.event_type}</span></td>
                <td style="font-family: 'JetBrains Mono', monospace; font-size: 12px; font-weight:700;">${log.patient_id}</td>
                <td style="font-weight: 600;">${log.operator}</td>
                <td style="color: var(--text-main); font-size: 12px;">${log.description}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error(e);
        tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: #f43f5e;">Fallo al conectar con el libro de auditoría.</td></tr>`;
    }
}

// 10. Premium Animation and Interactions
function initTilt() {
    const reducedMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reducedMotion) return;
    
    const nodes = document.querySelectorAll('[data-tilt]');
    const max = 8;

    nodes.forEach(el => {
        let raf = 0;
        let rect;

        function onMove(e) {
            if (!rect) return;
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            const mx = rect.width / 2;
            const my = rect.height / 2;
            const rx = ((y - my) / my) * -max;
            const ry = ((x - mx) / mx) * max;
            cancelAnimationFrame(raf);
            raf = requestAnimationFrame(() => {
                el.style.transform = `perspective(1100px) rotateX(${rx}deg) rotateY(${ry}deg) translateZ(0)`;
            });
        }

        function refreshRect() {
            rect = el.getBoundingClientRect();
        }

        function onEnter() {
            refreshRect();
        }

        function onLeave() {
            cancelAnimationFrame(raf);
            el.style.transform = '';
        }

        el.addEventListener('mouseenter', onEnter);
        el.addEventListener('mousemove', onMove);
        el.addEventListener('mouseleave', onLeave);
    });
}

function initOrbParallax() {
    const reducedMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reducedMotion) return;
    
    const wrap = document.querySelector('.bg-orbs');
    if (!wrap) return;
    
    let tick = null;
    window.addEventListener(
        'mousemove',
        e => {
            if (tick) return;
            tick = requestAnimationFrame(() => {
                tick = null;
                const px = e.clientX / window.innerWidth - 0.5;
                const py = e.clientY / window.innerHeight - 0.5;
                wrap.style.transform = `translate3d(${px * 28}px, ${py * 22}px, 0) scale(1.02)`;
            });
        },
        { passive: true }
    );
}

function runTabEntryAnimation(tabId) {
    // Animaciones de entrada desactivadas a petición del usuario
}
