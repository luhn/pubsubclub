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
		var uri = $(this).find("[name=uri]").val();
		ab.connect(uri, function(_session) {
			session = _session;
			log("Connected to " + uri);
			$("#subscribe, #publish").show();
			$("#connect").hide();
		}, function(code, reason) {
			log(reason, true)
		});
	});

	$("#subscribe").submit(function(e) {
		e.preventDefault();
		var uri = $(this).find("[name=uri]").val();
		log("Subscribed to " + uri);
		session.subscribe(
				uri,
			function(topic, event) {
				log(topic + ": " + event);
			});
	});

	$("#publish").submit(function(e) {
		e.preventDefault();
		var uri = $(this).find("[name=uri]").val();
		var content = $(this).find("[name=content]").val();
		session.call("http://example.com/pubsub#publish", {
			"channel": uri,
			"content": content
		}).then(function (res) {
			log("Published to " + uri + ": " + content);
		},
			function (error) {
				log(error.detail, true);
			});
	});
});
