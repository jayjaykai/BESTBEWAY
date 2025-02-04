const pageSize = 60;
const maxPages = 8;
let from = 0;
let currentPage = 0;
let loading = false;
let allDataLoaded = false;
let isArticlesLoading = false;
let query = '';
let maxSearchPage = 2;
const loadedProducts = new Set();
let currentTab = 'products';
let isFiltering = false;

async function performSearch() {
    let query = document.getElementById('search-query').value.trim();
    if (query === "") {
        alert("請輸入查詢關鍵詞！");
        return; 
    }
    searchProducts();
    searchArticles();
}

function showTab(tabId) {
    let productsTab = document.getElementById('products');
    let articlesTab = document.getElementById('articles');
    let productsButton = document.getElementById('productsButton');
    let articlesButton = document.getElementById('articlesButton');
    let hotKeywords = document.getElementById('search-container__hot');
    
    if (tabId === 'products') {
        productsTab.style.display = 'flex';
        articlesTab.style.display = 'none';
        hotKeywords.style.visibility = 'hidden';
        productsButton.classList.add('tabs__button--active');
        articlesButton.classList.remove('tabs__button--active');
    } else if (tabId === 'articles') {
        productsTab.style.display = 'none';
        hotKeywords.style.visibility = 'visible';
        articlesTab.style.display = 'flex';
        articlesButton.classList.add('tabs__button--active');
        productsButton.classList.remove('tabs__button--active');
        //如果文章還在搜尋中，一樣呈現lazy loading效果
        if (isArticlesLoading) {
            document.getElementById("loading-overlay").style.display = "block";
        } 
        else {
            document.getElementById("loading-overlay").style.display = "none";
        }
    }
    currentTab = tabId;
}

async function searchProducts() {
    from = 0;
    currentPage = 0;
    allDataLoaded = false;
    allCheckboxInitialized = false;
    loadedProducts.clear();
    loadedSellers.clear();

    document.getElementById('seller-filter').innerHTML = "";
    document.getElementById('product-list').innerHTML = "";

    query = document.getElementById('search-query').value;
    console.log('Search Query:', query);
    document.getElementById("loading-overlay").style.display = "block";
    await loadProducts();
    // scrollToProductList();

    if (currentTab === 'products') 
    {
        scrollToItemList(document.getElementById('product-list'));
        document.getElementById("loading-overlay").style.display = "none";
    } 
}

let loadedSellers = new Set();
let sellerFilterContainer = document.getElementById('seller-filter'); 
let allCheckboxInitialized = false; // 標記是否已經添加 ALL 篩選框

async function loadProducts() {
    if (loading || allDataLoaded) return;
    loading = true;
    let productList = document.getElementById('product-list');

    try {
        console.log("Loading products from:", from);
        let response = await fetch(`/api/product?query=${query}&from_=${from}&size=${pageSize}&current_page=${currentPage}&max_pages=${maxPages}`);
        let data = await response.json();
        console.log('Product Data received:', data);

        if (!Array.isArray(data) || data.length === 0) {
            allDataLoaded = true;
            loading = false;
            return;
        }

        from += pageSize;
        currentPage += 1;

        let newItemsAdded = false;

        // 如果 "ALL" 篩選框尚未添加，先添加
        if (!allCheckboxInitialized) {
            let allOption = document.createElement('div');
            allOption.className = 'seller-filter__option';
            allOption.innerHTML = `
                <input type="checkbox" class="seller-filter-all" id="seller-all" name="seller" value="all" checked>
                <label for="seller-all">ALL</label>
            `;
            sellerFilterContainer.appendChild(allOption);
            allCheckboxInitialized = true;
        }

        data.forEach(item => {
            if (!loadedProducts.has(item.title)) {
                loadedProducts.add(item.title);
                let div = document.createElement('div');
                div.className = 'product-list__item';
                div.innerHTML = `
                    <div class="product-list__image">
                        <img src="${item.image}" alt="${item.title}">
                    </div>
                    <div class="product-list__info">
                        <div class="product-list__title">${item.title}</div>
                        <div class="product-list__price">${item.price}</div>
                        <div class="product-list__seller">${item.seller}</div>
                        <a class="product-list__link" href="${item.link}" target="_blank">查看商品</a>
                    </div>
                `;

                productList.appendChild(div);
                newItemsAdded = true;
                // 加入賣家的篩選選項
                if (!loadedSellers.has(item.seller)) {
                    loadedSellers.add(item.seller);
                    let sellerOption = document.createElement('div');
                    sellerOption.className = 'seller-filter__option';
                    sellerOption.innerHTML = `
                        <input type="checkbox" class="seller-filter" id="seller-${item.seller}" name="seller" value="${item.seller}" checked>
                        <label for="seller-${item.seller}">${item.seller}</label>
                    `;
                    sellerFilterContainer.appendChild(sellerOption);
                }
                // 根據當前篩選條件決定是否顯示產品
                let selectedSellers = getSelectedSellers();
                if (selectedSellers.includes(item.seller.trim())) {
                    div.style.display = 'block';
                } else {
                    div.style.display = 'none';
                }
            }
        });

        if (!newItemsAdded) {
            allDataLoaded = true;
        }

    } catch (error) {
        console.error('Error loading products:', error);
    } finally {
        loading = false;
    }
}

async function searchCommonArticles() {
    let query = "寶寶常見問題";
    let url = `/api/article?query=${encodeURIComponent(query)}&pages=${1}`;

    let articleList = document.getElementById("article-common");
    let response = await fetch(url);

    if (!response.ok) {
        console.error("Search API request failed");
        articleList.innerHTML = "<p>Error loading articles.</p>";
        return;
    }

    let  articles = await response.json();
    displayCommonArticles(articles.search_results);
}

function displayCommonArticles(articles) {
    let articleList = document.getElementById("article-common");
    articleList.innerHTML = "";
    if (articles.length === 0) {
        articleList.innerHTML = "<p>No articles found.</p>";
        return;
    }

    console.log("common articles:", articles);
    let groupedArticles = Array.from({ length: maxSearchPage*10 }, () => []);

    articles.forEach((article, index) => {
        let groupIndex = (index + 1) % 10;
        groupedArticles[groupIndex].push(article);
    });

    for (let i = 0; i < 10; i++) {
        groupedArticles[i].forEach(article => {
            let articleItem = document.createElement("div");
            articleItem.className = "article-common-item";
    
            let articleTitle = document.createElement("h3");
            articleTitle.textContent = article.title;
            articleItem.appendChild(articleTitle);
    
            let articleSnippet = document.createElement("p");
            articleSnippet.textContent = article.snippet;
            articleItem.appendChild(articleSnippet);
    
            let articleLink = document.createElement("a");
            articleLink.href = article.link;
            articleLink.textContent = "Read more";
            articleLink.target = "_blank";
            articleItem.appendChild(articleLink);
    
            articleList.appendChild(articleItem);
        });
    }
}

async function searchArticles() {
    let query = document.getElementById("search-query").value;
    let url = `/api/article?query=${encodeURIComponent(query)}&pages=${maxSearchPage}`;

    let articleList = document.getElementById("article-list");
    let recommendedList = document.getElementById("article-product");

    document.getElementById("loading-overlay").style.display = "block";
    isArticlesLoading=true;

    articleList.innerHTML = "";
    recommendedList.innerHTML = "";

    try {
        let response = await fetch(url);

        if (!response.ok) {
            console.error("Search API request failed");
            articleList.innerHTML = "<p>Error loading articles.</p>";
            return;
        }

        let { search_results, recommended_items } = await response.json();
        await displayArticles(search_results);
        await displayRecommendedItems(recommended_items);

        if (currentTab === 'articles') {
            scrollToItemList(document.getElementById('article-product'));
            document.getElementById("loading-overlay").style.display = "none";
            isArticlesLoading=false;
        }
    } catch (error) {
        console.error("Failed to fetch articles:", error);
        articleList.innerHTML = "<p>Error loading articles.</p>";
    } finally {
        isArticlesLoading = false;
        if (currentTab === 'articles') {
            document.getElementById("loading-overlay").style.display = "none";
        }
        fetchHotKeywords();
    }
}

function scrollToItemList(item) {
    let itemList = item;
    let elementTopPosition = itemList.getBoundingClientRect().top + window.scrollY;
    let offset = 1;
    let navBarHeight = 60;

    window.scrollTo({
        top: elementTopPosition + offset - navBarHeight,
        behavior: 'smooth'
    });
}

async function displayArticles(articles) {
    let articleList = document.getElementById("article-list");
    articleList.innerHTML = "";
    console.log(articles);

    let groupedArticles = Array.from({ length: maxSearchPage*10 }, () => []);
    articles.forEach((article, index) => {
        let groupIndex = (index + 1) % (maxSearchPage*10);
        groupedArticles[groupIndex].push(article);
    });

    for (let i = 0; i < maxSearchPage*10; i++) {
        groupedArticles[i].forEach(article => {
            let articleItem = document.createElement("div");
            articleItem.className = "article-list__item";

            let title = document.createElement("h3");
            title.className = "article-list__item-title";
            title.textContent = article.title;
            articleItem.appendChild(title);

            let link = document.createElement("a");
            link.className = "article-list__item-link";
            link.href = article.link;
            link.target = "_blank";
            link.textContent = article.link;
            articleItem.appendChild(link);

            let snippet = document.createElement("p");
            snippet.className = "article-list__item-snippet";
            snippet.textContent = article.snippet;
            articleItem.appendChild(snippet);

            articleList.appendChild(articleItem);
        });
    }
}

async function displayRecommendedItems(recommendedItems) {
    let recommendedList = document.getElementById("article-product");
    recommendedList.innerHTML = "推薦商品： ";

    if (recommendedItems.length === 0) {
        recommendedList.innerHTML += "<p>No recommended items found.</p>";
        return;
    }

    recommendedItems.forEach(item => {
        let itemElement = document.createElement("span");
        itemElement.className = "recommended-items__item";
        
        let itemLink = document.createElement("a");
        itemLink.textContent = item;
        itemLink.onclick = function () {
            document.getElementById("search-query").value = item;
            showTab('products');
            searchProducts();
        };
        
        itemElement.appendChild(itemLink);
        itemElement.style.marginRight = "10px";
        recommendedList.appendChild(itemElement);
    });
}

// 減少重複觸發fetch /api/search_suggestions
let debounceTimer;
async function handleSearchInput() {
    const query = document.getElementById('search-query').value;
    const suggestionsDiv = document.getElementById('suggestions');

    if (query.length === 0) {
        suggestionsDiv.innerHTML = '';
        suggestionsDiv.classList.remove('visible');
        return;
    }

    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(async () => {
        try {
            let response = await fetch(`/api/search_suggestions?query=${query}`);
            let suggestions = await response.json();

            suggestionsDiv.innerHTML = '';
            if (Array.isArray(suggestions) && suggestions.length > 0) {
                suggestions.forEach(suggestion => {
                    const div = document.createElement('div');
                    div.className = 'suggestion-item';
                    div.textContent = suggestion;
                    suggestionsDiv.appendChild(div);

                    div.addEventListener('click', () => {
                        document.getElementById('search-query').value = suggestion;
                        suggestionsDiv.innerHTML = '';
                        suggestionsDiv.classList.remove('visible');
                    });
                });
                suggestionsDiv.classList.add('visible');
            } else {
                suggestionsDiv.classList.remove('visible');
            }
        } catch (error) {
            console.error('Error fetching suggestions:', error);
        }
    }, 300);
}

document.addEventListener('click', (event)=> {
    let searchInput = document.getElementById('search-query');
    let suggestionsDiv = document.getElementById('suggestions');

    if (!searchInput.contains(event.target) && !suggestionsDiv.contains(event.target)) {
        suggestionsDiv.classList.remove('visible');
    }
});

window.addEventListener('scroll', async() => {
    if (isFiltering) return;
    query = document.getElementById('search-query').value;
    if (query) {
        let element = document.getElementById('product-list');
        if (element && currentTab === 'products') {
            let rect = element.getBoundingClientRect();
            if (Math.floor(rect.bottom) <= window.innerHeight && !loading && !allDataLoaded && currentPage < maxPages) {
                console.log("loading!!!");
                document.getElementById("loading-overlay").style.display = "block";
                await loadProducts();
                document.getElementById("loading-overlay").style.display = "none";
            }
        }
    }
});

document.addEventListener('DOMContentLoaded', (event) => {
    let urlParams = new URLSearchParams(window.location.search);
    let queryParam = urlParams.get('query');
    if (queryParam) {
        document.getElementById('search-query').value = queryParam;
        searchProducts(queryParam);
    }

    let categoryLinks = document.querySelectorAll('.category');
    categoryLinks.forEach(link => {
        link.addEventListener('click', (event) => {
            event.preventDefault();
            let query = link.getAttribute('data-query');
            document.getElementById('search-query').value = query;
            searchProducts();
            searchArticles();
        });
    });
});

window.addEventListener('scroll', ()=> {
    var backToTopButton = document.getElementById('button-back-to-top');
    if (window.scrollY > 420) {
        backToTopButton.style.display = 'flex';
    } else {
        backToTopButton.style.display = 'none';
    }
});

// 點擊按鈕返回頂部
document.getElementById('button-back-to-top').addEventListener('click', ()=> {
    window.scrollTo({ top: 420, behavior: 'smooth' });
});

////////////////////////////////////// 熱搜關鍵字//////////////////////////////////////////
async function fetchHotKeywords() {
    try {
        const response = await fetch('/api/hot_keywords');
        if (response.ok) {
            const data = await response.json();
            const hotKeywordsContainer = document.getElementById('search-container__hot-content');
            
            hotKeywordsContainer.innerHTML = '';

            data.hot_keywords.forEach((item, index) => {
                const keywordSpan = document.createElement('span');
                keywordSpan.className = 'hot-keyword';
                // keywordSpan.innerText = `${item.keyword} (${item.score})`;
                if (index < data.hot_keywords.length - 1) {
                    keywordSpan.innerText = `${item.keyword}、`;
                } else {
                    keywordSpan.innerText = `${item.keyword}`;
                }
                keywordSpan.onclick = () => handleKeywordClick(item.keyword);
                hotKeywordsContainer.appendChild(keywordSpan);
            });
        } else {
            console.error('Failed to fetch hot keywords:', response.statusText);
        }
    } catch (error) {
        console.error('Error fetching hot keywords:', error);
    }
}
//處理點擊熱搜關鍵字
function handleKeywordClick(keyword) {
    document.getElementById('search-query').value = keyword;
    searchArticles();
}
////////////////////////////////////// 熱搜關鍵字//////////////////////////////////////////
function getSelectedSellers() {
    return Array.from(document.querySelectorAll('.seller-filter:checked'))
                .map(cb => cb.value.trim());
}

document.addEventListener('change', (event)=> {
    if (event.target.classList.contains('seller-filter')) {
        filterProducts();
    }
});

document.addEventListener('change', (event)=> {
    if (event.target.classList.contains('seller-filter-all')) {
        let allChecked = event.target.checked;
        isFiltering = true;
        // 點選All全部改變
        document.querySelectorAll('.seller-filter').forEach((checkbox)=>{
            checkbox.checked = allChecked;
        });
        filterProducts(); 
        setTimeout(() => { isFiltering = false; }, 500);
    }
});

function filterProducts() {
    let selectedSellers = getSelectedSellers();
    document.querySelectorAll('.product-list__item').forEach((item)=>{
            let seller = item.querySelector('.product-list__seller').textContent.trim();
            if (selectedSellers.includes(seller)) {
                item.style.display = 'block';
            } else {
                item.style.display = 'none';
            }
        }    
    );

    // 確認是否只有一個商品的情況
    let visibleProductItems = Array.from(document.querySelectorAll('.product-list__item'))
        .filter(item => item.offsetParent !== null);

    if (visibleProductItems.length === 1) {
        visibleProductItems[0].classList.add('single-product');
    } else {
        visibleProductItems.forEach(item => item.classList.remove('single-product'));
    }
}

searchCommonArticles();
fetchHotKeywords();
showTab('products');
