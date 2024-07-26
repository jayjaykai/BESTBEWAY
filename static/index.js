let from = 0;
const pageSize = 60;
let currentPage = 0;
const maxPages = 5;
let loading = false;
let query = '';

async function searchProducts() {
    from = 0;
    currentPage = 0;
    document.getElementById('product-list').innerHTML = '';
    query = "嬰兒"+document.getElementById('search-query').value;
    console.log(query);
    await loadProducts();
}

async function loadProducts() {
    if (loading) return;
    loading = true;
    try {
        console.log("from", from)
        const response = await fetch(`http://127.0.0.1:8000/product?query=${query}&from_=${from}&size=${pageSize}&current_page=${currentPage}&max_pages=${maxPages}`);
        const data = await response.json();
        console.log(data);
        if (data.length === 0) {
            // allDataLoaded = true;
            loading = false;
            return;
        }
        from += pageSize;
        currentPage += 1;
        const productList = document.getElementById('product-list');
        data.forEach(item => {
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
        });
    } catch (error) {
        console.error('Error loading products:', error);
    } finally {
        loading = false;
    }
}

window.addEventListener('scroll', () => {
    // 檢查特定元素是否進入視窗底部
    let element = document.getElementById('product-list');
    if (element) {
        let rect = element.getBoundingClientRect();
        // console.log('rect.bottom: ' + rect.bottom);
        // console.log('window.innerHeight: ' + window.innerHeight);
        // console.log("loading before checking scroll:", loading);
        if (rect.bottom <= window.innerHeight && !loading && currentPage < maxPages) {
            console.log("loading!!!");
            loadProducts();
        }
    }
});