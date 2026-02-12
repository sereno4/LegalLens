"""
LegalLens v1.3 - Versão LEVE e RÁPIDA para HF Spaces
✅ 100% CPU • Leitor de PDF • Build rápido • Sem timeouts
"""

import os
import warnings
import re
warnings.filterwarnings('ignore')

os.environ['TOKENIZERS_PARALLELISM'] = 'false'
os.environ['HF_HOME'] = '/tmp/.cache/huggingface'

import numpy as np
import gradio as gr

# Carregar dependências leves
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMER_AVAILABLE = True
except Exception as e:
    SENTENCE_TRANSFORMER_AVAILABLE = False

try:
    import faiss
    FAISS_AVAILABLE = True
except Exception as e:
    FAISS_AVAILABLE = False

# Dependências para PDF
try:
    import PyPDF2
    PDF_AVAILABLE = True
except Exception as e:
    PDF_AVAILABLE = False

class LegalLens:
    """Analisa documentos jurídicos detectando cláusulas críticas"""
    
    def __init__(self):
        # Cláusulas críticas em inglês/português misto (funciona melhor)
        self.critical_patterns = {
            'indenizacao': {
                'keywords': ['indenização', 'ressarcimento', 'danos', 'prejuízos', 'responsabilidade civil', 
                           'indemnification', 'damages', 'liability', 'compensation'],
                'description': 'Cláusulas de indenização e responsabilidade civil',
                'risk_level': 'high'
            },
            'rescisao_unilateral': {
                'keywords': ['rescisão unilateral', 'cancelamento unilateral', 'extinção unilateral', 'resilição',
                           'unilateral termination', 'unilateral cancellation', 'termination rights'],
                'description': 'Direito de rescindir contrato sem consentimento da outra parte',
                'risk_level': 'high'
            },
            'multa_contratual': {
                'keywords': ['multa contratual', 'penalidade', 'sanção contratual', 'cláusula penal',
                           'contractual penalty', 'penalty clause', 'liquidated damages'],
                'description': 'Multas e penalidades contratuais',
                'risk_level': 'medium'
            },
            'confidencialidade': {
                'keywords': ['confidencialidade', 'sigilo', 'informação confidencial', 'não divulgação',
                           'confidentiality', 'non-disclosure', 'proprietary information'],
                'description': 'Obrigações de confidencialidade e sigilo',
                'risk_level': 'medium'
            },
            'exclusividade': {
                'keywords': ['exclusividade', 'exclusivo', 'único fornecedor', 'único prestador',
                           'exclusivity', 'exclusive', 'sole provider'],
                'description': 'Cláusulas de exclusividade comercial',
                'risk_level': 'medium'
            },
            'foro_eleicao': {
                'keywords': ['foro de eleição', 'foro competente', 'jurisdição', 'tribunal competente',
                           'choice of forum', 'jurisdiction', 'competent court'],
                'description': 'Definição do foro/jurisdição para resolução de disputas',
                'risk_level': 'low'
            }
        }
    
    def _split_sentences(self, text):
        """Divide texto em sentenças"""
        text = re.sub(r'\s+', ' ', text)
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if len(s.strip()) > 10]
    
    def _keyword_search(self, text):
        """Busca baseada em palavras-chave"""
        found_clauses = []
        text_lower = text.lower()
        
        for clause_type, clause_info in self.critical_patterns.items():
            for keyword in clause_info['keywords']:
                if keyword.lower() in text_lower:
                    sentences = self._split_sentences(text)
                    matching_sentence = None
                    
                    for sentence in sentences:
                        if keyword.lower() in sentence.lower():
                            matching_sentence = sentence.strip()
                            break
                    
                    if matching_sentence:
                        found_clauses.append({
                            'type': clause_type,
                            'keyword': keyword,
                            'sentence': matching_sentence,
                            'risk_level': clause_info['risk_level'],
                            'description': clause_info['description']
                        })
                    break
        
        return found_clauses
    
    def analyze_document(self, text):
        """Analisa documento jurídico"""
        if not text or len(text.strip()) < 50:
            return {"error": "Texto muito curto. Envie pelo menos 50 caracteres."}
        
        clauses = self._keyword_search(text)
        
        # Ordenar por risco
        risk_order = {'high': 3, 'medium': 2, 'low': 1}
        clauses.sort(key=lambda x: risk_order.get(x['risk_level'], 0), reverse=True)
        
        return {
            'clauses_found': clauses,
            'total_clauses': len(clauses)
        }

def extract_text_from_pdf(pdf_file):
    """Extrai texto de arquivo PDF"""
    if not PDF_AVAILABLE:
        return None, "PyPDF2 não disponível"
    
    try:
        with open(pdf_file.name, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            
            text = re.sub(r'\s+', ' ', text).strip()
            return text, None
            
    except Exception as e:
        return None, f"Erro ao ler PDF: {str(e)}"

def analyze_contract(text_input, pdf_input):
    """Função principal para análise"""
    text = ""
    
    # Priorizar PDF se fornecido
    if pdf_input is not None:
        extracted_text, error = extract_text_from_pdf(pdf_input)
        if error:
            return (
                f"<div style='color:#c62828; padding:20px; background:#ffebee; border-radius:12px; font-size:15px; font-weight:bold; text-align:center;'>❌ {error}</div>",
                "Erro ao processar PDF"
            )
        elif not extracted_text or len(extracted_text) < 50:
            return (
                "<div style='color:#d32f2f; padding:20px; text-align:center; background:#ffebee; border-radius:12px; font-size:16px; font-weight:bold;'>⚠️ PDF sem conteúdo suficiente para análise</div>",
                "PDF vazio ou muito curto"
            )
        text = extracted_text
    elif text_input and len(text_input.strip()) >= 50:
        text = text_input
    else:
        return (
            "<div style='color:#d32f2f; padding:20px; text-align:center; background:#ffebee; border-radius:12px; font-size:16px; font-weight:bold;'>⚠️ Envie um texto com pelo menos 50 caracteres ou um arquivo PDF</div>",
            "Entrada inválida"
        )
    
    try:
        analyzer = LegalLens()
        result = analyzer.analyze_document(text)
        
        if 'error' in result:
            return (
                f"<div style='color:#c62828; padding:20px; background:#ffebee; border-radius:12px; font-size:15px; font-weight:bold; text-align:center;'>❌ {result['error']}</div>",
                "Erro na análise"
            )
        
        clauses = result['clauses_found']
        
        if not clauses:
            resultado_html = """
            <div style='text-align:center; padding:40px; background:#e8f5e9; border-radius:16px;'>
                <div style='font-size:60px; margin-bottom:20px;'>✅</div>
                <h2 style='color:#2e7d32; margin:0 0 15px 0; font-size:28px;'>Nenhuma cláusula crítica detectada!</h2>
                <p style='color:#37474f; font-size:16px; max-width:600px; margin:0 auto; line-height:1.6;'>
                    O documento analisado não contém as cláusulas críticas monitoradas pelo sistema.
                </p>
            </div>
            """
            return resultado_html, "Documento seguro"
        
        # Resultados com cláusulas encontradas
        resultado_html = f"""
        <div style='max-width:850px; margin:0 auto; font-family:Segoe UI, system-ui;'>
            <div style='text-align:center; background:#ffebee; border-radius:16px; padding:25px; margin-bottom:25px; border:1px solid #ffcdd2;'>
                <div style='font-size:56px; margin-bottom:15px;'>⚠️</div>
                <h2 style='color:#c62828; margin:0 0 15px 0; font-size:28px;'>Cláusulas Críticas Detectadas</h2>
                <div style='font-size:20px; font-weight:700; color:#d32f2f; margin-bottom:15px;'>{len(clauses)} cláusulas identificadas</div>
                <div style='width:100%; max-width:320px; height:18px; background:rgba(211,47,47,0.1); border-radius:9px; margin:0 auto; overflow:hidden;'>
                    <div style='width:{min(len(clauses)*20, 100)}%; height:100%; background:#d32f2f; border-radius:9px;'></div>
                </div>
            </div>
        """
        
        # Classificar cláusulas por nível de risco
        high_risk = [c for c in clauses if c['risk_level'] == 'high']
        medium_risk = [c for c in clauses if c['risk_level'] == 'medium']
        low_risk = [c for c in clauses if c['risk_level'] == 'low']
        
        risk_sections = []
        if high_risk:
            risk_sections.append(('ALTO', '#d32f2f', high_risk))
        if medium_risk:
            risk_sections.append(('MÉDIO', '#f57c00', medium_risk))
        if low_risk:
            risk_sections.append(('BAIXO', '#2e7d32', low_risk))
        
        for risk_level, color, clauses_list in risk_sections:
            resultado_html += f"""
            <div style='margin-bottom:25px;'>
                <h3 style='color:{color}; margin:0 0 15px 0; font-size:20px; display:flex; align-items:center; gap:10px;'>
                    <span style='font-size:24px;'>{'🔴' if risk_level=='ALTO' else '🟠' if risk_level=='MÉDIO' else '🟢'}</span>
                    Risco {risk_level} ({len(clauses_list)} cláusulas)
                </h3>
            """
            
            for clause in clauses_list:
                resultado_html += f"""
                <div style='background:rgba({211 if risk_level=='ALTO' else 245 if risk_level=='MÉDIO' else 46}, {47 if risk_level=='ALTO' else 124 if risk_level=='MÉDIO' else 125}, {47 if risk_level=='ALTO' else 0 if risk_level=='MÉDIO' else 47}, 0.08); border-left:4px solid {color}; padding:18px; margin:12px 0; border-radius:10px;'>
                    <div style='font-weight:600; color:{color}; margin-bottom:8px; font-size:16px;'>
                        {clause['description']}
                    </div>
                    <div style='font-family:monospace; background:white; padding:12px; border-radius:8px; margin:8px 0; font-size:14px; line-height:1.5;'>
                        "{clause['sentence']}"
                    </div>
                    <div style='color:#616161; font-size:13px; margin-top:8px;'>
                        Palavra-chave: <strong>{clause['keyword']}</strong>
                    </div>
                </div>
                """
            
            resultado_html += "</div>"
        
        resultado_html += """
            <div style='background:#e8f5e9; border-radius:16px; padding:20px; margin-top:25px; text-align:center;'>
                <div style='font-weight:600; font-size:16px; color:#1b5e20; margin-bottom:12px;'>
                    ℹ️ Como funciona a análise
                </div>
                <div style='color:#37474f; line-height:1.6; font-size:14px; max-width:650px; margin:0 auto;'>
                    O LegalLens analisa documentos jurídicos procurando por <strong>6 tipos de cláusulas críticas</strong> 
                    usando busca avançada por palavras-chave em português e inglês.
                    Cada cláusula detectada é classificada por nível de risco e apresentada com contexto relevante.
                </div>
            </div>
        </div>
        """
        
        summary = f"⚠️ {len(clauses)} cláusulas críticas detectadas ({len(high_risk)} alto risco)"
        return resultado_html, summary
        
    except Exception as e:
        erro_html = f"""
        <div style='color:#c62828; padding:25px; background:#ffebee; border-radius:16px; font-size:16px; line-height:1.6; text-align:center;'>
            <div style='font-weight:bold; margin-bottom:15px; font-size:20px;'>❌ Erro durante análise</div>
            <div style='font-family:monospace; background:#ffcdd2; padding:15px; border-radius:10px; margin-top:10px;'>
                {str(e)[:200]}
            </div>
            <div style='margin-top:15px; font-size:14px; color:#546e7a;'>
                💡 Dica: Verifique se o PDF contém texto selecionável ou envie texto com pelo menos 50 caracteres.
            </div>
        </div>
        """
        return erro_html, "Erro na análise"

# ============================================
# INTERFACE GRADIO
# ============================================

with gr.Blocks(theme=gr.themes.Soft(), title="LegalLens - Analisador Jurídico") as demo:
    gr.Markdown("""
    <div style='text-align:center; max-width:800px; margin:0 auto 30px auto; padding:0 15px;'>
        <div style='background:linear-gradient(135deg, #ffebee, #ffcdd2); border-radius:24px; padding:30px; box-shadow:0 6px 20px rgba(211,47,47,0.15);'>
            <h1 style='font-size:42px; font-weight:800; margin:0 0 15px 0; color:#c62828; line-height:1.15;'>⚖️ LegalLens</h1>
            <p style='font-size:19px; color:#5d4037; line-height:1.6; max-width:650px; margin:0 auto; font-weight:400;'>
                Analisador jurídico inteligente que detecta cláusulas críticas em contratos e documentos legais
            </p>
            <div style='background:#ffcdd2; border-radius:14px; padding:15px; margin-top:20px; display:inline-block;'>
                <p style='margin:0; color:#b71c1c; font-size:16px; font-weight:600;'>
                    ✅ 100% CPU • ✅ Leitor de PDF • ✅ Build rápido
                </p>
            </div>
        </div>
    </div>
    """)
    
    with gr.Row(equal_height=False):
        with gr.Column(scale=1, min_width=450):
            gr.Markdown("### 📄 Envie seu Documento")
            
            with gr.Tab("📝 Texto"):
                text_input = gr.Textbox(
                    label=None,
                    lines=8,
                    placeholder="Cole aqui seu contrato, termo de uso, acordo ou qualquer documento jurídico...",
                    show_label=False
                )
            
            with gr.Tab("📄 PDF"):
                pdf_input = gr.File(
                    label="Upload PDF",
                    file_types=[".pdf"],
                    type="filepath"
                )
            
            with gr.Row():
                analyze_btn = gr.Button(
                    "🔍 Analisar Documento",
                    variant="primary",
                    size="lg"
                )
                clear_btn = gr.Button("🗑️ Limpar", size="lg")
            
            gr.Markdown("""
            <div style='background:#ffebee; border-radius:14px; padding:18px; margin-top:25px; font-size:14px; line-height:1.6;'>
                <p style='margin:0 0 12px 0; font-weight:600; color:#c62828; font-size:15px;'>ℹ️ Instruções:</p>
                <p style='margin:0 0 8px 0;'>• Suporta texto direto ou upload de PDF</p>
                <p style='margin:0 0 8px 0;'>• PDF deve conter texto selecionável (não escaneado)</p>
                <p style='margin:0 0 8px 0;'>• Mínimo de 50 caracteres para análise</p>
                <p style='margin:12px 0 0 0; color:#b71c1c; font-weight:500; background:#ffcdd2; padding:10px; border-radius:10px;'>
                    ⚠️ Este é um assistente jurídico. Não substitui orientação de advogado qualificado.
                </p>
            </div>
            """)
        
        with gr.Column(scale=1, min_width=500):
            gr.Markdown("### 🎯 Resultado da Análise")
            result_output = gr.HTML(
                value="<div style='text-align:center; padding:50px 30px; color:#78909c; min-height:400px; background:#fafbfc; border-radius:18px;'><p style='font-size:24px; margin-bottom:20px; font-weight:600; color:#455a64;'>Aguardando documento para análise...</p><p style='font-size:16px; opacity:0.85; max-width:600px; margin:0 auto; line-height:1.6;'>Envie um texto ou PDF para que o LegalLens analise procurando por cláusulas críticas como indenização, rescisão unilateral, multas contratuais e outras.</p></div>"
            )
    
    # Funções de botão
    analyze_btn.click(
        analyze_contract,
        inputs=[text_input, pdf_input],
        outputs=[result_output]
    )
    
    def clear_inputs():
        return "", None, "<div style='text-align:center; padding:50px 30px; color:#78909c; min-height:400px; background:#fafbfc; border-radius:18px;'><p style='font-size:24px; margin-bottom:20px; font-weight:600; color:#455a64;'>Aguardando documento para análise...</p><p style='font-size:16px; opacity:0.85; max-width:600px; margin:0 auto; line-height:1.6;'>Envie um texto ou PDF para que o LegalLens analise procurando por cláusulas críticas como indenização, rescisão unilateral, multas contratuais e outras.</p></div>"
    
    clear_btn.click(
        clear_inputs,
        inputs=[],
        outputs=[text_input, pdf_input, result_output]
    )

# Rodapé corrigido
gr.Markdown("""
<div style='text-align:center; margin-top:40px; padding:25px; color:#546e7a; font-size:14px; line-height:1.7; max-width:800px; margin-left:auto; margin-right:auto; border-top:1px solid #e0e0e0; background:#fafafa; border-radius:14px;'>
    <p style='margin:8px 0; font-weight:700; color:#c62828; font-size:16px;'>LegalLens v1.3 • Analisador Jurídico com IA</p>
    
    <div style='display:flex; justify-content:center; gap:30px; flex-wrap:wrap; margin:20px 0; max-width:700px; margin-left:auto; margin-right:auto; font-size:13px;'>
        <div style='text-align:left; max-width:220px;'>
            <p style='font-weight:600; color:#c62828; margin:6px 0;'>🔍 Tecnologia</p>
            <p style='margin:4px 0; line-height:1.5;'>• Busca por palavras-chave<br>• PyPDF2 para PDFs<br>• Processamento leve<br>• Multilíngue (PT/EN)</p>
        </div>
        <div style='text-align:left; max-width:220px;'>
            <p style='font-weight:600; color:#c62828; margin:6px 0;'>💼 Aplicações</p>
            <p style='margin:4px 0; line-height:1.5;'>• Revisão de contratos<br>• Due diligence<br>• Compliance jurídico<br>• Gestão de riscos</p>
        </div>
        <div style='text-align:left; max-width:220px;'>
            <p style='font-weight:600; color:#c62828; margin:6px 0;'>⚠️ Nota</p>
            <p style='margin:4px 0; line-height:1.5;'>• Demo CPU<br>• Uso ético<br>• Open-source</p>
        </div>
    </div>
    
    <p style='margin:15px 0 0 0; padding-top:15px; border-top:1px dashed #bdbdbd; font-style:italic; color:#455a64; font-size:13px;'>
        ✨ Sistema de análise jurídica com IA — diferencial competitivo para vagas de Engenheiro de IA/ML
    </p>
</div>
""")

if __name__ == "__main__":
    demo.launch()
