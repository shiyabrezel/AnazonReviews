let page = 1;
const pageSize = 10;
let totalReviews = 0;
let topWordsLoadedPositive = false;
let topWordsLoadedNegative = false;
let topWordsLoadedAll = false;

function updatePaginationInfo() {
    const totalPages = Math.ceil(totalReviews / pageSize);
    $('#page-info').text(`Page ${page} of ${totalPages}`);
    $('#next-page').prop('disabled', page >= totalPages);
}

function loadReviews(reset = false) {
    if (reset) {
        page = 1;
        $('#reviews-container').empty();
    }
    console.log("Loading reviews...");
    const sentiment = $('#sentiment').val();
    console.log("Selected sentiment:", sentiment);
    $.get('/reviews', { sentiment: sentiment, page: page, page_size: pageSize }, function(data) {
        console.log("Data received:", data);
        data.reviews.forEach(review => {
            $('#reviews-container').append(`
                <div class="review">
                    <div class="review-title">${review.title}</div>
                    <div class="review-text">${review.text}</div>
                </div>
            `);
        });
        totalReviews = data.total_reviews;
        updatePaginationInfo();

        // Load top words only if not already loaded for the selected sentiment
        if ((sentiment === 'positive' && !topWordsLoadedPositive) ||
            (sentiment === 'negative' && !topWordsLoadedNegative) ||
            (!sentiment && !topWordsLoadedAll)) {
            loadTopWords(sentiment);
            if (sentiment === 'positive') topWordsLoadedPositive = true;
            if (sentiment === 'negative') topWordsLoadedNegative = true;
            if (!sentiment) topWordsLoadedAll = true;
        }
    }).fail(function() {
        alert('Error loading reviews');
    });
}

function loadTopWords(sentiment) {
    console.log("Loading top words...");
    $.get('/top_words', { sentiment: sentiment }, function(data) {
        console.log("Top words received:", data);
        $('#top-words-container').html('<h3>Top Words:</h3>' + data.map(word => word[0]).join(', '));
    }).fail(function() {
        alert('Error loading top words');
    });
}

function searchSimilarWords() {
    const word = $('#word-search').val();
    const sentiment = $('#sentiment').val();
    console.log("Searching for similar words to:", word);
    $.get('/similar_words', { word: word, sentiment: sentiment }, function(data) {
        console.log("Similar words received:", data);
        $('#similar-words-container').html('<h3>Similar Words:</h3>' + data.join(', '));
        highlightSimilarWords(data);
    }).fail(function() {
        alert('Error searching for similar words');
    });
}


function highlightSimilarWords(words) {
    $('#reviews-container .review').each(function() {
        let titleText = $(this).find('.review-title').text();
        let reviewText = $(this).find('.review-text').text();

        words.forEach(word => {
            const regex = new RegExp(`\\b${word}\\b`, 'gi');
            titleText = titleText.replace(regex, `<span class="highlight">${word}</span>`);
            reviewText = reviewText.replace(regex, `<span class="highlight">${word}</span>`);
        });

        $(this).find('.review-title').html(titleText);
        $(this).find('.review-text').html(reviewText);
    });
}

$('#load-reviews').click(function() {
    loadReviews(true);
});

$('#sentiment').change(function() {
    loadReviews(true);
});

$('#next-page').click(function() {
    const totalPages = Math.ceil(totalReviews / pageSize);
    if (page < totalPages) {
        page++;
        loadReviews();
    }
});

$('#export-reviews').click(function() {
    const sentiment = $('#sentiment').val();
    const url = `/export_reviews?sentiment=${sentiment}`;
    window.location.href = url;
});

$('#search-word').click(function() {
    searchSimilarWords();
});

// Load initial reviews
loadReviews(true);





