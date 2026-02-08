    function fetch1() {
    // Get the value from the input field
    const name = document.getElementById('customer_name').value;
    // Send AJAX request to Django view with name as a query parameter
    fetch(`/drivers/missions/fetch1/?name=${encodeURIComponent(name)}`)  // Specify full URL path
        .then(response => response.json())
        .then(data => {
            document.getElementById("customer_phone").value = data.phone;
            document.getElementById("receiving_location").value = data.address;
        });
}

    function fetch2() {
    // Get the value from the input field
    const name = document.getElementById('edit-customer_name').value;
    // Send AJAX request to Django view with name as a query parameter
    fetch(`/drivers/missions/fetch1/?name=${encodeURIComponent(name)}`)  // Specify full URL path
        .then(response => response.json())
        .then(data => {
            document.getElementById("edit-customer_phone").value = data.phone;
            document.getElementById("edit-receiving_location").value = data.address;
        });
}

