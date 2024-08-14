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
    // await searchProducts();
    // await searchArticles();
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
    await loadProducts();
}

async function loadProducts() {
    if (loading || allDataLoaded) return;
    loading = true;
    let productList = document.getElementById('product-list');

    let loadingElement = document.createElement('div');
    loadingElement.id = 'loading';
    loadingElement.textContent = 'Loading...';
    productList.appendChild(loadingElement);

    try {
        console.log("Loading products from:", from);
        let response = await fetch(`/api/product?query=${query}&from_=${from}&size=${pageSize}&current_page=${currentPage}&max_pages=${maxPages}`);
        let data = await response.json();
        console.log('Product Data received:', data);

        if (!Array.isArray(data) || data.length === 0) {
            allDataLoaded = true;
            loading = false;
            productList.removeChild(loadingElement);
            return;
        }

        from += pageSize;
        currentPage += 1;
        productList.removeChild(loadingElement);

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


async function searchArticles() {
    let query = document.getElementById("search-query").value;
    let url = `/api/article?query=${encodeURIComponent(query)}&pages=${maxSearchPage}`;

    let articleList = document.getElementById("article-list");
    articleList.innerHTML = "<p>Loading...</p>";

    let recommendedList = document.getElementById("article-product");
    recommendedList.innerHTML = "";

    let response = await fetch(url);

    if (!response.ok) {
        console.error("Search API request failed");
        articleList.innerHTML = "<p>Error loading articles.</p>";
        return;
    }

    let { search_results, recommended_items } = await response.json();
    displayArticles(search_results);
    displayRecommendedItems(recommended_items);
}

// function displayArticles(articles) {
//     let articleList = document.getElementById("article-list");
//     articleList.innerHTML = "";
//     console.log('Article Data received:', articles);

//     articles.forEach(article => {
//         let articleItem = document.createElement("div");
//         articleItem.className = "article-list__item";

//         let title = document.createElement("h3");
//         title.className = "article-list__item-title";
//         title.textContent = article.title;
//         articleItem.appendChild(title);

//         let link = document.createElement("a");
//         link.className = "article-list__item-link";
//         link.href = article.link;
//         link.target = "_blank";
//         link.textContent = article.link;
//         articleItem.appendChild(link);

//         let snippet = document.createElement("p");
//         snippet.className = "article-list__item-snippet";
//         snippet.textContent = article.snippet;
//         articleItem.appendChild(snippet);

//         articleList.appendChild(articleItem);
//     });
// }

function displayArticles(articles) {
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


function displayRecommendedItems(recommendedItems) {
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
            searchProducts();
            showTab('products');
        };
        
        itemElement.appendChild(itemLink);
        itemElement.style.marginRight = "10px";
        recommendedList.appendChild(itemElement);
    });
}

window.addEventListener('scroll', () => {
    query = document.getElementById('search-query').value;
    if (query) {
        let element = document.getElementById('product-list');
        if (element && currentTab === 'products') {
            let rect = element.getBoundingClientRect();
            if (Math.floor(rect.bottom) <= window.innerHeight && !loading && !allDataLoaded && currentPage < maxPages) {
                console.log("loading!!!");
                loadProducts();
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

showTab('products');
