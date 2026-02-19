from pypdf import PdfReader
reader = PdfReader("/home/fernando/Área de trabalho/Orcamento/CONTRATO - Phelippe Zandarin.pdf")
text = ""
for page in reader.pages:
    text += page.extract_text()
print(text)
