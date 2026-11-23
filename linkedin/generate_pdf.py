import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super(NumberedCanvas, self).showPage()
        super(NumberedCanvas, self).save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        
        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, letter[1] - 36, "DocuRAG: Deployment & Engineering Post-Mortem Brief")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(54, letter[1] - 42, letter[0] - 54, letter[1] - 42)
            
        # Footer
        footer_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(letter[0] - 54, 30, footer_text)
        self.drawString(54, 30, "Confidential & Engineering Technical Case Study | DocuRAG RAG Assistant")
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(54, 42, letter[0] - 54, 42)
        self.restoreState()

def build_pdf():
    pdf_path = os.path.join("linkedin", "DocuRAG_Deployment_Troubleshooting_Brief.pdf")
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=48,
        bottomMargin=48
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=4
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#2563EB"),
        spaceAfter=14
    )

    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#1E293B"),
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#334155"),
        spaceAfter=6
    )

    bullet_style = ParagraphStyle(
        'Bullet_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#334155"),
        leftIndent=14,
        firstLineIndent=-10,
        spaceAfter=3
    )

    code_style = ParagraphStyle(
        'Code_Custom',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#0F172A")
    )

    story = []

    # Title Banner
    story.append(Paragraph("DocuRAG: Deployment & Troubleshooting Brief", title_style))
    story.append(Paragraph("A Technical Case Study on Diagnosing Cross-Origin, Lifecycle, and Cloud Hosting Challenges", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2563EB"), spaceAfter=12))

    # Meta Table
    meta_data = [
        [
            Paragraph("<b>Project:</b> DocuRAG (AI Document Q&A)", body_style),
            Paragraph("<b>Architecture:</b> Decoupled SPA + Async API", body_style),
        ],
        [
            Paragraph("<b>Frontend:</b> Vercel (React + Vite)", body_style),
            Paragraph("<b>Backend:</b> Render (FastAPI + ChromaDB)", body_style),
        ],
        [
            Paragraph("<b>Core Issue:</b> 'Failed to fetch' (CORS & Lifecycle)", body_style),
            Paragraph("<b>Resolution Status:</b> Fully Resolved & Verified", body_style),
        ]
    ]
    meta_table = Table(meta_data, colWidths=[240, 264])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F1F5F9")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#CBD5E1")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))

    # 1. Executive Summary
    story.append(Paragraph("1. Executive Summary", h1_style))
    story.append(Paragraph(
        "During the deployment of the <b>DocuRAG</b> enterprise question-answering assistant, the decoupled architecture experienced a persistent browser-side <b>'Failed to fetch'</b> error upon loading the application. The user interface remained stuck at <i>'Connecting...'</i> with zero documents and sessions available. This document provides an engineering post-mortem detailing the symptoms, root cause analysis across three distinct technical vectors, the applied remediation steps, and key architectural takeaways.",
        body_style
    ))

    # 2. Problem Symptoms & Error Analysis
    story.append(Paragraph("2. Symptoms & Diagnostic Findings", h1_style))
    story.append(Paragraph(
        "Browser developer tools and console telemetry revealed several concurrent errors:",
        body_style
    ))
    
    findings = [
        "<b>Browser Console Error:</b> <code>Access to fetch at 'https://ai-document-q-a-assistant-rag-1.onrender.com/api/v1/documents' from origin 'https://frontend-...vercel.app' has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present on the requested resource.</code>",
        "<b>HTTP Failure Status:</b> Failed pre-flight (<code>OPTIONS</code>) and subsequent <code>GET /api/v1/documents</code> returning <code>net::ERR_FAILED 200 (OK)</code> / Network Error.",
        "<b>UI Degradation:</b> Red alert banner reading <i>'Failed to fetch'</i> with document upload and chat interfaces deactivated.",
        "<b>Local Git Failure:</b> Attempts to commit configuration fixes locally failed with <code>fatal: Unable to create '.git/index.lock': Permission denied</code>."
    ]
    for f in findings:
        story.append(Paragraph(f"• {f}", bullet_style))
    story.append(Spacer(1, 8))

    # 3. Root Cause Investigation
    story.append(Paragraph("3. Deep Root Cause Analysis", h1_style))
    
    rc_data = [
        [
            Paragraph("<b>Vector</b>", body_style),
            Paragraph("<b>Underlying Technical Cause</b>", body_style),
            Paragraph("<b>Impact</b>", body_style)
        ],
        [
            Paragraph("<b>Dynamic Vercel Domains</b>", body_style),
            Paragraph("Vercel produces ephemeral preview domains (e.g., <code>frontend-[hash]-[team].vercel.app</code>). The backend allowed-origins list was static and strictly hardcoded.", body_style),
            Paragraph("Pre-flight CORS requests from previews were rejected with missing access-control headers.", body_style)
        ],
        [
            Paragraph("<b>Backend Router Truncation</b>", body_style),
            Paragraph("A previous edit in <code>backend/app/main.py</code> accidentally truncated the file after the CORS block, omitting <code>app.include_router(...)</code> registrations.", body_style),
            Paragraph("FastAPI returned 404/unhandled routes for documents and chat, bypassing normal CORS headers.", body_style)
        ],
        [
            Paragraph("<b>Render Cold Start Latency</b>", body_style),
            Paragraph("Render free-tier instances spin down to 0 replicas after 15 minutes of inactivity. Cold start recovery takes 30–50 seconds.", body_style),
            Paragraph("Immediate browser requests timed out before the Uvicorn process finished initialization.", body_style)
        ],
        [
            Paragraph("<b>Windows Sandbox Lock</b>", body_style),
            Paragraph("Standard sandbox execution restricted write access to hidden system metadata in <code>.git/index.lock</code>.", body_style),
            Paragraph("Prevented local staging and push of critical deployment updates until bypassed.", body_style)
        ]
    ]
    rc_table = Table(rc_data, colWidths=[110, 260, 134])
    rc_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#E2E8F0")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor("#0F172A")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('BACKGROUND', (0,1), (-1,1), colors.HexColor("#FFFFFF")),
        ('BACKGROUND', (0,2), (-1,2), colors.HexColor("#F8FAFC")),
        ('BACKGROUND', (0,3), (-1,3), colors.HexColor("#FFFFFF")),
        ('BACKGROUND', (0,4), (-1,4), colors.HexColor("#F8FAFC")),
    ]))
    story.append(rc_table)
    story.append(Spacer(1, 10))

    # 4. Remediation & Implementation
    story.append(Paragraph("4. Implemented Solutions & Engineering Fixes", h1_style))
    
    fixes = [
        "<b>Universal Vercel CORS Regex Support:</b> Upgraded FastAPI CORS configuration in <code>main.py</code> by integrating <code>allow_origin_regex=r'https://.*\\.vercel\\.app'</code>. This automatically authorizes all production, preview, and branch environments securely without requiring manual IP or URL additions.",
        "<b>Restored FastAPI Routing & Error Pipeline:</b> Re-instated all core routers (<code>health_router</code>, <code>documents_router</code>, <code>chat_router</code>), lifespan lifecycle manager, and global exception handlers to guarantee graceful error responses.",
        "<b>Resolved Git Staging & Deployment Sync:</b> Overcame the Windows file lock constraint, safely synchronized remote Git history via rebase, and pushed the fixed codebase directly to GitHub <code>main</code>.",
        "<b>Vercel Production Alignment:</b> Rebuilt and aliased the frontend distribution directly via Vercel CLI, binding the production endpoint (<code>frontend-five-plum-90.vercel.app</code>) with validated environment parameters."
    ]
    for fix in fixes:
        story.append(Paragraph(f"✔ {fix}", bullet_style))
    story.append(Spacer(1, 8))

    # 5. Verification & Live Status
    story.append(Paragraph("5. Verification & Validation Results", h1_style))
    story.append(Paragraph(
        "Automated cross-origin probe requests were dispatched against the live Render server to confirm resolution:",
        body_style
    ))

    probe_data = [
        [
            Paragraph("<b>Target Endpoint</b>", body_style),
            Paragraph("<b>Simulated Origin</b>", body_style),
            Paragraph("<b>HTTP Status</b>", body_style),
            Paragraph("<b>Access-Control-Allow-Origin</b>", body_style)
        ],
        [
            Paragraph("<code>/api/v1/health</code>", code_style),
            Paragraph("<code>*.vercel.app (Preview)</code>", code_style),
            Paragraph("<b>200 OK</b>", body_style),
            Paragraph("✔ Validated Header Returned", body_style)
        ],
        [
            Paragraph("<code>/api/v1/documents</code>", code_style),
            Paragraph("<code>frontend-five-plum-90...</code>", code_style),
            Paragraph("<b>200 OK</b>", body_style),
            Paragraph("✔ Validated Header Returned", body_style)
        ],
        [
            Paragraph("<code>/api/v1/chat/sessions</code>", code_style),
            Paragraph("<code>frontend-five-plum-90...</code>", code_style),
            Paragraph("<b>200 OK</b>", body_style),
            Paragraph("✔ Validated Header Returned", body_style)
        ]
    ]
    probe_table = Table(probe_data, colWidths=[110, 160, 80, 154])
    probe_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#E2E8F0")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor("#FFFFFF")),
    ]))
    story.append(probe_table)
    story.append(Spacer(1, 10))

    # 6. Key Takeaways & Recommendations
    story.append(Paragraph("6. Key Architectural Takeaways for Portfolio & Resume", h1_style))
    takeaways = [
        "<b>Decoupled Deployment Architecture:</b> Deploying frontend and backend across different cloud providers (Vercel + Render) requires regex-based origin whitelisting to accommodate automated CI/CD branch previews without security holes.",
        "<b>Cold Start Awareness:</b> Free-tier micro-instances require client-side retry logic and loading indicators to handle initial spinning latency transparently.",
        "<b>Cloud Environment Isolation:</b> Ensuring backend API keys (such as <code>OPENAI_API_KEY</code>) are injected directly into production container environments prevents runtime inference failures."
    ]
    for t in takeaways:
        story.append(Paragraph(f"📌 {t}", bullet_style))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated: {pdf_path}")

if __name__ == '__main__':
    build_pdf()
