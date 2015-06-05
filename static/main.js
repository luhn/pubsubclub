$(function() {
	function log(message, error) {
		var $el = $("<li></li>");
		$el.text(message);
		if(error) {
			$el.css("color", "red");
		}
		$el.appendTo("#log");
	}

	var session;
	$("#subscribe, #publish").hide()
	$("#connect").submit(function(e) {
		e.preventDefault();
		ab.connect($(this).find("[name=uri]").val(), function(_session) {
			session = _session;
			log("Connected.");
			$("#subscribe, #publish").show();
			$("#connect").hide();
		}, function(code, reason) {
			log(reason, true)
		});
	});

	$("#subscribe").submit(function(e) {
		e.preventDefault();
		session.subscribe(
			$(this).find("[name=uri]").val(),
			function(topic, event) {
				log(topic + ": " + event);
			});
	});

	$("#publish").submit(function(e) {
		e.preventDefault();
		session.call("http://example.com/pubsub#publish", {
			"channel": $(this).find("[name=uri]").val(),
			"content": $(this).find("[name=content]").val()
		}).then(function (res) {},
			function (error) {
				log(error.detail, true);
			});
	});
});
