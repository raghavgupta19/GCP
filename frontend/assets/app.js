document.getElementById("dataForm").addEventListener("submit", async (e) => {
  e.preventDefault();

  const formData = new FormData(e.target);
  const data = Object.fromEntries(formData.entries());

  const response = await fetch("http://136.109.169.56:3000/submit", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data)
  });

  if (response.ok) {
    window.location.href = "success.html";
  } else {
    alert("Submission failed");
  }
});

