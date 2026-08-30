import urllib.request

pdf_path = r"D:\Enterprise-AI\gsvai-enterprise-ai\docs\6Month_AI_Career_Plan.pdf"

with open(pdf_path, "rb") as f:
    pdf_data = f.read()

boundary = "----GSVAIFormBoundary"

body = (
    f"--{boundary}\r\n"
    'Content-Disposition: form-data; name="file"; filename="6Month_AI_Career_Plan.pdf"\r\n'
    "Content-Type: application/pdf\r\n"
    "\r\n"
).encode("utf-8")

body += pdf_data

body += (
    f"\r\n--{boundary}--\r\n"
).encode("utf-8")

request = urllib.request.Request(
    "http://127.0.0.1:8000/ai-workspace/upload",
    data=body,
    headers={
        "Content-Type": f"multipart/form-data; boundary={boundary}"
    },
    method="POST",
)

print("Uploading:", pdf_path)

response = urllib.request.urlopen(request)

print("STATUS:", response.status)
print(response.read().decode("utf-8"))
