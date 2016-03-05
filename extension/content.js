document.addEventListener("DOMContentLoaded", function(e) {
	var host = location.hostname;
	// both of these websites do not trigger full page reloads when songs/videos change
	// we'll need to setup mutation observers and wait for the correct elements to load
	// this will be trial and error to find the best ones
	if (host === 'www.pandora.com') {
		console.log('Pandora was detected');
		setupObserver(handlePandora);
	} else if (host === 'www.youtube.com') {
		console.log('Youtube was detected');
		setupObserver(handleYoutube);
	}
});

// sets up an object that will observe pages for changes to the DOM
// will call the handler function do determine how to handle each change
function setupObserver(handler) {
	var observer = new WebKitMutationObserver(function(mutations) {
		mutations.forEach(function(mutation) {
			for (var i = 0; i < mutation.addedNodes.length; i++) {
				handler(mutation.addedNodes[i]);
			}
		});
	});
	observer.observe(document, { childList: true, subtree: true });
}

function handlePandora(addedNode) {
	if (addedNode.classList && addedNode.classList.contains('lyrics')) {
		console.log('Item lyrics div loaded');
		// the item lyrics div just got loaded so now we'll add a hook
		// for when songs actually change
		document.getElementsByClassName('artistSummary')[0].addEventListener('DOMSubtreeModified', function(e) {
			//console.log(e);
			var title = document.getElementsByClassName('songTitle')[0].text;
			var artist = document.getElementsByClassName('artistSummary')[0].text;
			// for some reason this event triggers twice when a song switches.
			// when it triggers the first time, there is no artist yet
			// this "hack" will wait until we have an artist and title before updating the boot
			if (title && artist) {
				console.log(artist + ' - ' + title);
			} else {
				console.debug('First song trigger didn\'t contain artist or song title.');
			}
		});
	}
}

function handleYoutube(addedNode) {
	// this check happens when you're already on youtube and you click a video
	if (addedNode.id === 'watch7-main-container' || 
		// this check happens the first time you navigate to youtube. it's a bit slower because it's not the correct element... but it works
		addedNode.id === 'appbar-guide-menu') {
			
		console.log('Main content probably loaded at this point');
		// grab song info since we think it's here
		console.log(document.getElementById('eow-title').title);
	}
}
