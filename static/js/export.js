
window.addEventListener("DOMContentLoaded", () => {
  const capture = document.getElementById("capture");
  const btnPNG = document.getElementById("btnPNG");
  const btnPDF = document.getElementById("btnPDF");

  async function toCanvas() {
    return await html2canvas(capture, { scale: 2, useCORS: true });
  }

  btnPNG?.addEventListener("click", async () => {
    const canvas = await toCanvas();
    const link = document.createElement("a");
    link.download = "SEU-schedule.png";
    link.href = canvas.toDataURL("image/png");
    link.click();
  });

  btnPDF?.addEventListener("click", async () => {
    const canvas = await toCanvas();
    const imgData = canvas.toDataURL("image/png");
    const { jsPDF } = window.jspdf;
    const pdf = new jsPDF({ orientation: "landscape", unit: "pt", format: "a4" });
    const pageWidth = pdf.internal.pageSize.getWidth();
    const pageHeight = pdf.internal.pageSize.getHeight();
    // Fit image to page with margins
    const margin = 24;
    const w = pageWidth - margin*2;
    const ratio = canvas.height / canvas.width;
    const h = w * ratio;
    const y = (pageHeight - h)/2;
    pdf.addImage(imgData, "PNG", margin, y, w, h);
    pdf.save("SEU-schedule.pdf");
  });
});
