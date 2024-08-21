let from = 0;
const pageSize = 60;
let currentPage = 0;
const maxPages = 10;
let loading = false;
let allDataLoaded = false;
let query = '';
let maxSearchPage = 2;
const loadedProducts = new Set();
let currentTab = 'products';

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
    
    if (tabId === 'products') {
        productsTab.style.display = 'flex';
        articlesTab.style.display = 'none';
        productsButton.classList.add('tabs__button--active');
        articlesButton.classList.remove('tabs__button--active');
    } else if (tabId === 'articles') {
        productsTab.style.display = 'none';
        articlesTab.style.display = 'flex';
        articlesButton.classList.add('tabs__button--active');
        productsButton.classList.remove('tabs__button--active');
    }
    currentTab = tabId;
}

async function searchProducts() {
    from = 0;
    currentPage = 0;
    allDataLoaded = false;
    loadedProducts.clear();

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
        }
    } catch (error) {
        console.error("Failed to fetch articles:", error);
        articleList.innerHTML = "<p>Error loading articles.</p>";
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

window.addEventListener('scroll', async() => {
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
            searchProducts(query);
            searchArticles(query);
        });
    });
});

searchCommonArticles();
showTab('products');
