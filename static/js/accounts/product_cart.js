// FILE: static/js/accounts/product_cart.js (v4.1 - 最終修正版)

document.addEventListener('DOMContentLoaded', () => {

    // --- 元素獲取 ---
    const productCards = document.querySelectorAll('.product-card');
    const cartItemsContainer = document.getElementById('cart-items');
    const cartSubtotalPriceEl = document.getElementById('cart-subtotal-price');
    const cartTaxPriceEl = document.getElementById('cart-tax-price');
    const cartTotalPriceEl = document.getElementById('cart-total-price');
    const checkoutBtn = document.querySelector('.checkout-btn');

    // --- 全局變數 ---
    window.cart = {}; // 使用物件，以 product_id 為鍵

    // --- 讀取已購買模組 ---
    let purchasedModuleIds = [];
    const purchasedDataElement = document.getElementById('purchased-modules-data');
    if (purchasedDataElement) {
        try {
            purchasedModuleIds = JSON.parse(purchasedDataElement.textContent);
        } catch (e) {
            console.error('無法解析已購買模組數據:', e);
        }
    }

    // --- 函式定義 ---
    window.updateCartUI = function () {
        cartItemsContainer.innerHTML = '';
        // 【核心修正】正確的檢查物件是否為空的方式
        if (Object.keys(window.cart).length === 0) {
            cartItemsContainer.innerHTML = '<p class="cart-empty-msg">您的購物車是空的。</p>';
        } else {
            let subtotal = 0;
            Object.values(window.cart).forEach(item => {
                subtotal += item.priceValue;
                const itemEl = document.createElement('div');
                itemEl.className = 'cart-item';
                itemEl.innerHTML = `
                    <div class="cart-item-info">
                        <span class="cart-item-name">${item.name}</span>
                        <span class="cart-item-plan">${item.planText}</span>
                    </div>
                    <div class="cart-item-price">
                        <span>NT$</span>
                        <span>${item.priceValue.toLocaleString()}</span>
                    </div>
                    <button class="cart-item-remove" data-id="${item.id}">&times;</button>
                `;
                cartItemsContainer.appendChild(itemEl);
            });
            const tax = Math.round(subtotal * 0.05);
            const finalTotal = subtotal + tax;
            cartSubtotalPriceEl.textContent = `NT$${subtotal.toLocaleString()}`;
            cartTaxPriceEl.textContent = `NT$${tax.toLocaleString()}`;
            cartTotalPriceEl.textContent = `NT$${finalTotal.toLocaleString()}`;
        }
    }

    // --- 事件監聽器 ---

    productCards.forEach(card => {
        const priceEl = card.querySelector('.product-price');
        const radios = card.querySelectorAll('input[type="radio"]');
        const addToCartBtn = card.querySelector('.add-to-cart-btn');

        radios.forEach(radio => {
            radio.addEventListener('change', () => {
                if (radio.checked) {
                    priceEl.textContent = radio.dataset.price;
                }
            });
        });

        addToCartBtn.addEventListener('click', () => {
            const productId = card.dataset.productId;

            // 【功能實現】購買前檢查
            if (purchasedModuleIds.includes(productId)) {
                alert('您已訂閱此模組，無需重複購買。如需延長訂閱，請等待未來開放的續訂功能。');
                return; // 阻止執行後續的加入購物車邏輯
            }

            const productName = card.querySelector('h3').textContent;
            const selectedRadio = card.querySelector('input[type="radio"]:checked');

            window.cart[productId] = {
                id: productId,
                name: productName,
                plan: selectedRadio.value,
                planText: selectedRadio.parentElement.textContent.trim(),
                priceText: selectedRadio.dataset.price,
                priceValue: parseInt(selectedRadio.dataset.price.replace(/NT\$|,/g, '')),
            };

            addToCartBtn.textContent = '已加入！';
            setTimeout(() => {
                addToCartBtn.textContent = '加入購物車';
            }, 1500);

            window.updateCartUI();
        });
    });

    cartItemsContainer.addEventListener('click', (event) => {
        if (event.target.classList.contains('cart-item-remove')) {
            const productId = event.target.dataset.id;
            delete window.cart[productId];
            window.updateCartUI();
        }
    });

    if (checkoutBtn) {
        checkoutBtn.addEventListener('click', function () {
            const cartArray = Object.values(window.cart);
            if (cartArray.length === 0) {
                alert('您的購物車是空的，請先加入商品！');
                return;
            }

            this.disabled = true;
            this.textContent = '產生訂單中...';

            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
            const cartItemsForBackend = cartArray.map(item => ({
                id: item.id,
                plan: item.plan,
                name: item.name
            }));
            const checkoutUrl = this.dataset.checkoutUrl;

            fetch(checkoutUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                },
                body: JSON.stringify({
                    items: cartItemsForBackend
                }),
            })
                .then(response => {
                    // 如果伺服器回傳錯誤(4xx, 5xx)，我們嘗試解析 JSON 錯誤訊息
                    if (!response.ok) {
                        return response.json().then(err => {
                            throw new Error(err.message || `伺服器回應錯誤: ${response.status}`);
                        });
                    }
                    // 如果成功，回傳的是 HTML 頁面，我們需要將其渲染
                    return response.text();
                })
                .then(html => {
                    // 【核心修改】將整個頁面替換為綠界重導向頁面的內容
                    document.open();
                    document.write(html);
                    document.close();
                })
                .catch(error => {
                    console.error('Checkout Fetch Error:', error);
                    alert('結帳請求失敗：' + error.message);
                    this.disabled = false;
                    this.textContent = '前往結帳';
                });
        });
    }
});