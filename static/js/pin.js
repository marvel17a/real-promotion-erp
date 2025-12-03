<script>
document.getElementById("pincode").addEventListener("input", function () {
    let pin = this.value.trim();

    if (pin.length === 6 && /^[0-9]{6}$/.test(pin)) {
        fetch(`/api/pincode_lookup/${pin}`)
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    document.getElementById("city").value = data.city;
                    document.getElementById("state").value = data.state;
                }
            });
    }
});
</script>
