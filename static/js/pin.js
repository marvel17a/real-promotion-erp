document.addEventListener("DOMContentLoaded", () => {
    const pincode = document.getElementById("pincode");
    const city = document.getElementById("city");
    const district = document.getElementById("district");
    const state = document.getElementById("state");

    pincode.addEventListener("input", async () => {
        const pin = pincode.value.trim();

        if (pin.length !== 6 || !/^\d{6}$/.test(pin)) {
            city.innerHTML = "<option value=''>Select Area</option>";
            district.value = "";
            state.value = "";
            return;
        }

        try {
            const res = await fetch(https://api.postalpincode.in/pincode/${pin});
            const data = await res.json();

            if (!data || data[0].Status !== "Success") {
                city.innerHTML = "<option value=''>Select Area</option>";
                district.value = "";
                state.value = "";
                return;
            }

            const offices = data[0].PostOffice;

            // district & state accurate
            district.value = offices[0].District;
            state.value = offices[0].State;

            city.innerHTML = "<option value=''>Please Select Area</option>";
            offices.forEach(o => {
                let area = o.Name || o.BranchType || o.Block || o.District;
                let op = document.createElement("option");
                op.value = area;
                op.textContent = area;
                city.appendChild(op);
            });

        } catch (e) {
            console.log("Pincode JS error", e);
        }
    });
});
