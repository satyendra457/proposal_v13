$(document).ready(function () {
	// open thank you dialog box on accept button click
    // open Revise request dialog box on revise quotation button click
    
    $("#accept_proposal").click(function () {
        $(this).css("pointer-events", "none");
        if (this.value) {
            $.ajax({
                type: 'GET',
                url: '/my/proposal',
                dataType: 'json',
                data: {
                    "revise_id": this.value,
                    "qty_accepted": $("#qty_accepted").val(),
                },
                success: function (result) {
                    window.location.href = "/";

                }
            });
        }
    });

});