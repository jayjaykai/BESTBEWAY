let from = 0;
const pageSize = 60;
let currentPage = 0;
const maxPages = 10;
let loading = false;
let allDataLoaded = false;
let query = '';
const loadedProducts = new Set(); // 用於存儲已加載的產品標題

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
}

async function searchProducts() {
    from = 0;
    currentPage = 0;
    allDataLoaded = false;
    loadedProducts.clear();

    document.getElementById('product-list').innerHTML = '';

    query = document.getElementById('search-query').value;
    console.log(query);
    await loadProducts();
}

async function loadProducts() {
    if (loading || allDataLoaded) return;
    loading = true;
    try {
        console.log("from", from)
        const response = await fetch(`/api/product?query=${query}&from_=${from}&size=${pageSize}&current_page=${currentPage}&max_pages=${maxPages}`);
        const data = await response.json();
        console.log(data);
        if (data.items.length === 0) {
            allDataLoaded = true;
            loading = false;
            return;
        }
        // if (currentPage === 0) {
        //     from = 0;  // 重置 from 以確保 Google Shopping 爬取從 0 開始
        // } else {
        //     from += pageSize;
        // }
        from += pageSize;
        currentPage += 1;
        const productList = document.getElementById('product-list');
        let newItemsAdded = false;
        data.items.forEach(item => {
            // 檢查產品是否已經加載過
            if (!loadedProducts.has(item.title)) {
                loadedProducts.add(item.title); // 將產品標題加入集合
                const div = document.createElement('div');
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
            if (!newItemsAdded) {
                allDataLoaded = true;
            }
        });
    } catch (error) {
        console.error('Error loading products:', error);
    } finally {
        loading = false;
    }
}

window.addEventListener('scroll', () => {
    query = document.getElementById('search-query').value;
    if (query){
        let element = document.getElementById('product-list');
        if (element) {
            let rect = element.getBoundingClientRect();
            // console.log('rect.bottom: ' + Math.floor(rect.bottom));
            // console.log('window.innerHeight: ' + window.innerHeight);
            if (Math.floor(rect.bottom) <= window.innerHeight && !loading && !allDataLoaded && currentPage < maxPages) {
                console.log("loading!!!");
                loadProducts();
            }
        }
    }
});

document.addEventListener('DOMContentLoaded', (event) => {
    const urlParams = new URLSearchParams(window.location.search);
    const queryParam = urlParams.get('query');
    if (queryParam) {
        document.getElementById('search-query').value = queryParam;
        searchProducts(queryParam);
    }

    // Add event listener to category links
    const categoryLinks = document.querySelectorAll('.category');
    categoryLinks.forEach(link => {
        link.addEventListener('click', (event) => {
            event.preventDefault();
            const query = link.getAttribute('data-query');
            document.getElementById('search-query').value = query;
            searchProducts(query);
        });
    });
});


// let from = 0;
// const pageSize = 60;
// let currentPage = 0;
// const maxPages = 5;
// let loading = false;
// let allDataLoaded = false;
// let query = '';

// async function searchProducts() {
//     from = 0;
//     currentPage = 0;
//     allDataLoaded = false;

//     document.getElementById('product-list').innerHTML = '';

//     query = document.getElementById('search-query').value;
//     console.log(query);
//     await loadProducts();
// }

// async function loadProducts() {
//     if (loading || allDataLoaded) return;
//     loading = true;
//     try {
//         console.log("from", from)
//         const response = await fetch(`/api/product?query=${query}&from_=${from}&size=${pageSize}&current_page=${currentPage}&max_pages=${maxPages}`);
//         const data = await response.json();
//         console.log(data);
//         if (data.length === 0) {
//             allDataLoaded = true;
//             loading = false;
//             return;
//         }
//         from += pageSize;
//         currentPage += 1;
//         const productList = document.getElementById('product-list');
//         data.forEach(item => {
//             const div = document.createElement('div');
//             div.className = 'product-list__item';
//             div.innerHTML = `
//                 <div class="product-list__image">
//                         <img src="${item.image}" alt="${item.title}">
//                 </div>
//                 <div class="product-list__info">
//                     <div class="product-list__title">${item.title}</div>
//                     <div class="product-list__price">${item.price}</div>
//                     <div class="product-list__seller">${item.seller}</div>
//                     <a class="product-list__link" href="${item.link}" target="_blank">查看商品</a>
//                 </div>
//             `;
//             productList.appendChild(div);
//         });
//     } catch (error) {
//         console.error('Error loading products:', error);
//     } finally {
//         loading = false;
//     }
// }

// // window.addEventListener('scroll', () => {
// //     // 檢查特定元素是否進入視窗底部
// //     let element = document.getElementById('product-list');
// //     if (element) {
// //         let rect = element.getBoundingClientRect();
// //         console.log('rect.bottom: ' + rect.bottom);
// //         console.log('element.scrollHeight: ' + element.scrollHeight);
// //         console.log('element.scrollTop: ' + element.scrollTop);
// //         console.log('element.clientHeight: ' + element.clientHeight);
// //         console.log("loading before checking scroll:", loading);
// //         if ((element.scrollHeight - element.scrollTop) <= element.clientHeight && !loading && !allDataLoaded && currentPage < maxPages) {
// //             console.log("loading!!!");
// //             loadProducts();
// //         }
// //     }
// // });
// window.addEventListener('scroll', () => {
//     // 檢查特定元素是否進入視窗底部
//     let element = document.getElementById('product-list');
//     if (element) {
//         let rect = element.getBoundingClientRect();
//         // console.log('rect.bottom: ' + rect.bottom);
//         // console.log('window.innerHeight: ' + window.innerHeight);
//         // console.log("loading before checking scroll:", loading);
//         if (rect.bottom <= window.innerHeight && !loading && !allDataLoaded && currentPage < maxPages) {
//             console.log("loading!!!");
//             loadProducts();
//         }
//     }
// });