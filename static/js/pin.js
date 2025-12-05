// static/js/pincode.js
document.addEventListener("DOMContentLoaded", () => {
    const pinInput = document.getElementById("pincode");
    const citySelect = document.getElementById("city");
    const districtInput = document.getElementById("district");
    const stateInput = document.getElementById("state");

    if (!pinInput || !citySelect || !districtInput || !stateInput) {
        return; // safety if script loaded on other pages
    }

    pinInput.addEventListener("input", async () => {
        const pin = pinInput.value.trim();

        // Basic validation
        if (pin.length !== 6 || !/^\d{6}$/.test(pin)) {
            citySelect.innerHTML = "<option value=''>Select City/Area</option>";
            districtInput.value = "";
            stateInput.value = "";
            return;
        }

        try {
            const res = await fetch(https://api.postalpincode.in/pincode/${pin});
            const data = await res.json();

            if (!data || data[0].Status !== "Success") {
                citySelect.innerHTML = "<option value=''>Select City/Area</option>";
                districtInput.value = "";
                stateInput.value = "";
                return;
            }

            const offices = data[0].PostOffice;

            // district & state from first office (these are reliable)
            districtInput.value = offices[0].District || "";
            stateInput.value = offices[0].State || "";

            // build city / area dropdown
            citySelect.innerHTML = "<option value=''>Select City/Area</option>";

            offices.forEach(o => {
                // Prefer Block (taluka) then Name, fallback to District
                const label = o.Block || o.Name || o.District || "";
                if (!label) return;

                const opt = document.createElement("option");
                opt.value = label;
                opt.textContent = label;
                citySelect.appendChild(opt);
            });

        } catch (err) {
            console.log("Pincode API error:", err);
            citySelect.innerHTML = "<option value=''>Select City/Area</option>";
            districtInput.value = "";
            stateInput.value = "";
        }
    });
});
