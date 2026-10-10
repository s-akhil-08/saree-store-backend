(function() {
    'use strict';

    // Only run on the Product Add page
    var pathname = window.location.pathname;
    if (pathname.indexOf('/admin/products/product/add/') === -1 && pathname.indexOf('/admin/products/product/add') === -1) {
        return;
    }

    // -----------------------------------------------------------------
    // Batch Product State
    // -----------------------------------------------------------------
    var batchState = {
        enabled: false,
        activeIndex: 0,
        products: [
            { id: 1, name: 'Product 1', saved: false, savedId: null, data: {}, files: new Map() }
        ]
    };

    function initBatchCreator() {
        var form = document.getElementById('product_form');
        if (!form || form.dataset.batchInitialized === 'true') return;
        form.dataset.batchInitialized = 'true';

        // 1. Create Top Batch Mode Container
        var batchContainer = document.createElement('div');
        batchContainer.id = 'batch-product-creator-wrapper';
        batchContainer.className = 'w-full mb-6 transition-all duration-200';
        batchContainer.innerHTML = `
            <div class="card bg-base-100 border border-base-content/15 shadow-sm rounded-xl overflow-hidden">
                <!-- Top Toolbar Header -->
                <div class="p-4 bg-base-200/50 border-b border-base-content/10 flex flex-wrap items-center justify-between gap-3">
                    <div class="flex items-center gap-3">
                        <div class="w-9 h-9 rounded-lg bg-primary/10 text-primary flex items-center justify-center font-bold text-lg">
                            ⚡
                        </div>
                        <div>
                            <h3 class="text-sm font-bold text-base-content m-0">Multi-Product Batch Creator</h3>
                            <p class="text-xs text-base-content/60 m-0">Add multiple products with live upload percentage, one-click copy & sequential saving</p>
                        </div>
                    </div>

                    <div class="flex items-center gap-3">
                        <!-- Mode Toggle Button -->
                        <button type="button" id="btn-toggle-batch-mode" class="btn btn-sm btn-outline border-base-content/20 gap-2">
                            <span id="batch-mode-toggle-icon">⚡</span>
                            <span id="batch-mode-toggle-text">Enable Multi-Product Mode</span>
                        </button>
                    </div>
                </div>

                <!-- Batch Management Body (Visible when Batch Mode is Active) -->
                <div id="batch-management-body" class="p-4 space-y-4" style="display: none;">
                    <!-- Stepper & Quick Actions -->
                    <div class="flex flex-wrap items-center justify-between gap-4 pb-3 border-b border-base-content/10">
                        <div class="flex items-center gap-3">
                            <span class="text-xs font-semibold text-base-content/70">Total Products to Add:</span>
                            <div class="join border border-base-content/20 rounded-lg overflow-hidden bg-base-100">
                                <button type="button" id="btn-batch-decrease" class="btn btn-xs join-item px-3 font-bold">−</button>
                                <span id="batch-count-display" class="join-item px-4 py-1 text-xs font-bold flex items-center justify-center min-w-[36px] bg-base-200/40">2</span>
                                <button type="button" id="btn-batch-increase" class="btn btn-xs join-item px-3 font-bold">+</button>
                            </div>
                        </div>

                        <!-- Top Save All Button -->
                        <div class="flex items-center gap-2">
                            <button type="button" id="btn-batch-save-all-top" class="btn btn-sm btn-primary gap-2 shadow-sm font-semibold">
                                <span>💾</span> Save All Products (<span class="batch-total-count">2</span>)
                            </button>
                        </div>
                    </div>

                    <!-- Product Tabs Bar -->
                    <div class="flex flex-wrap items-center gap-2" id="batch-tabs-bar">
                        <!-- Dynamic Product Tabs injected here -->
                    </div>

                    <!-- Copy Info Bar (Shown on Product 2 and higher) -->
                    <div id="batch-copy-bar" class="p-3 bg-primary/5 border border-primary/20 rounded-lg flex flex-wrap items-center justify-between gap-3" style="display: none;">
                        <div class="flex items-center gap-2">
                            <span class="text-primary text-sm">📋</span>
                            <span class="text-xs text-base-content/80 font-medium">Quick Fill: Copy Category, Brand, Description, and New Arrival settings from Product 1.</span>
                        </div>
                        <button type="button" id="btn-copy-from-prev" class="btn btn-xs btn-primary btn-outline font-semibold gap-1">
                            <span>📋</span> Copy from Product 1
                        </button>
                    </div>

                    <!-- Active Product Status Banner -->
                    <div id="batch-active-status-banner" class="text-xs py-1 px-3 rounded bg-base-200/60 text-base-content/70 flex items-center justify-between">
                        <span>Currently Editing: <strong id="batch-active-label" class="text-primary">Product 1</strong></span>
                        <span id="batch-active-status-badge" class="badge badge-xs badge-neutral">Draft</span>
                    </div>
                </div>
            </div>
        `;

        // Insert at the top of content
        var contentMain = document.getElementById('content-main') || form.parentNode;
        contentMain.insertBefore(batchContainer, form);

        // 2. Add Bottom Save All Button into Submit Line
        var submitRow = form.querySelector('.submit-row');
        if (submitRow) {
            var bottomSaveAll = document.createElement('button');
            bottomSaveAll.type = 'button';
            bottomSaveAll.id = 'btn-batch-save-all-bottom';
            bottomSaveAll.className = 'btn btn-primary gap-2 font-bold shadow-md';
            bottomSaveAll.style.display = 'none';
            bottomSaveAll.innerHTML = '<span>💾</span> Save All Products (<span class="batch-total-count">2</span>)';
            submitRow.insertBefore(bottomSaveAll, submitRow.firstChild);
        }

        // 3. Attach Event Listeners
        var toggleBtn = document.getElementById('btn-toggle-batch-mode');
        var batchBody = document.getElementById('batch-management-body');
        var decreaseBtn = document.getElementById('btn-batch-decrease');
        var increaseBtn = document.getElementById('btn-batch-increase');
        var copyBtn = document.getElementById('btn-copy-from-prev');
        var saveAllTop = document.getElementById('btn-batch-save-all-top');
        var saveAllBottom = document.getElementById('btn-batch-save-all-bottom');

        toggleBtn.addEventListener('click', function() {
            batchState.enabled = !batchState.enabled;
            window._batchModeActive = batchState.enabled;

            if (batchState.enabled) {
                batchBody.style.display = 'block';
                toggleBtn.classList.add('btn-primary');
                toggleBtn.classList.remove('btn-outline');
                document.getElementById('batch-mode-toggle-icon').textContent = '✓';
                document.getElementById('batch-mode-toggle-text').textContent = 'Batch Mode Active';
                if (saveAllBottom) saveAllBottom.style.display = 'inline-flex';

                if (batchState.products.length < 2) {
                    setProductCount(2);
                } else {
                    renderTabs();
                }
            } else {
                batchBody.style.display = 'none';
                toggleBtn.classList.remove('btn-primary');
                toggleBtn.classList.add('btn-outline');
                document.getElementById('batch-mode-toggle-icon').textContent = '⚡';
                document.getElementById('batch-mode-toggle-text').textContent = 'Enable Multi-Product Mode';
                if (saveAllBottom) saveAllBottom.style.display = 'none';
            }
        });

        decreaseBtn.addEventListener('click', function() {
            if (batchState.products.length > 2) {
                setProductCount(batchState.products.length - 1);
            }
        });

        increaseBtn.addEventListener('click', function() {
            if (batchState.products.length < 10) {
                setProductCount(batchState.products.length + 1);
            }
        });

        copyBtn.addEventListener('click', function() {
            copyDetailsFromProduct(0, batchState.activeIndex);
        });

        if (saveAllTop) saveAllTop.addEventListener('click', executeBatchSave);
        if (saveAllBottom) saveAllBottom.addEventListener('click', executeBatchSave);
    }

    // -----------------------------------------------------------------
    // Set Product Count & Render Tabs
    // -----------------------------------------------------------------
    function setProductCount(count) {
        while (batchState.products.length < count) {
            var newIdx = batchState.products.length;
            batchState.products.push({
                id: newIdx + 1,
                name: 'Product ' + (newIdx + 1),
                saved: false,
                savedId: null,
                data: {},
                files: new Map()
            });
        }

        while (batchState.products.length > count) {
            batchState.products.pop();
        }

        if (batchState.activeIndex >= count) {
            batchState.activeIndex = count - 1;
        }

        renderTabs();
    }

    function renderTabs() {
        var count = batchState.products.length;
        document.getElementById('batch-count-display').textContent = count;
        document.querySelectorAll('.batch-total-count').forEach(function(el) { el.textContent = count; });

        var tabsBar = document.getElementById('batch-tabs-bar');
        tabsBar.innerHTML = '';

        batchState.products.forEach(function(prod, idx) {
            var isActive = idx === batchState.activeIndex;
            var tabBtn = document.createElement('button');
            tabBtn.type = 'button';
            tabBtn.className = 'btn btn-sm ' + (isActive ? 'btn-primary' : 'btn-outline border-base-content/20 bg-base-100') + ' gap-2 transition-all';
            
            var badgeClass = 'badge-neutral';
            var badgeText = 'Draft';
            if (prod.saved) {
                badgeClass = 'badge-success text-success-content';
                badgeText = 'Saved ✓';
            } else if (prod.hasError) {
                badgeClass = 'badge-error text-error-content';
                badgeText = 'Error ⚠️';
            }

            tabBtn.innerHTML = `
                <span>${prod.saved ? '✓' : (idx + 1)}</span>
                <span class="font-bold">${prod.data['name'] || prod.name}</span>
                <span class="badge badge-xs ${badgeClass}">${badgeText}</span>
            `;

            tabBtn.addEventListener('click', function() {
                switchToProduct(idx);
            });

            tabsBar.appendChild(tabBtn);
        });

        // Add Product Tab Button
        if (count < 10) {
            var addBtn = document.createElement('button');
            addBtn.type = 'button';
            addBtn.className = 'btn btn-sm btn-ghost border border-dashed border-base-content/30 gap-1 text-xs';
            addBtn.innerHTML = '<span>+</span> Add Product';
            addBtn.addEventListener('click', function() {
                setProductCount(batchState.products.length + 1);
                switchToProduct(batchState.products.length - 1);
            });
            tabsBar.appendChild(addBtn);
        }

        // Update Copy Bar visibility
        var copyBar = document.getElementById('batch-copy-bar');
        if (copyBar) {
            copyBar.style.display = batchState.activeIndex > 0 ? 'flex' : 'none';
        }

        // Update Active Status Bar
        var activeProd = batchState.products[batchState.activeIndex];
        document.getElementById('batch-active-label').textContent = activeProd.data['name'] || activeProd.name;
        var statusBadge = document.getElementById('batch-active-status-badge');
        if (activeProd.saved) {
            statusBadge.className = 'badge badge-xs badge-success text-success-content';
            statusBadge.textContent = 'Saved (' + (activeProd.savedId || 'Done') + ')';
        } else if (activeProd.hasError) {
            statusBadge.className = 'badge badge-xs badge-error text-error-content';
            statusBadge.textContent = 'Has Validation Errors';
        } else {
            statusBadge.className = 'badge badge-xs badge-neutral';
            statusBadge.textContent = 'Draft (Unsaved)';
        }
    }

    // -----------------------------------------------------------------
    // Inline Helper Methods
    // -----------------------------------------------------------------
    function clearInlineGroup(prefix) {
        var group = document.querySelector('#' + prefix + '-group, div[id*="' + prefix + '"]');
        if (!group) return;

        var rows = group.querySelectorAll('tr.form-row:not(.empty-form):not(.add-row), div.form-row:not(.empty-form):not(.add-row), tr[id^="' + prefix + '-"]:not([id$="-empty"])');
        rows.forEach(function(r) {
            r.remove();
        });

        var totalInp = document.querySelector('#id_' + prefix + '-TOTAL_FORMS');
        if (totalInp) {
            totalInp.value = '0';
        }
    }

    function addInlineRows(prefix, count) {
        var group = document.querySelector('#' + prefix + '-group, div[id*="' + prefix + '"]');
        if (!group) return;
        var addBtn = group.querySelector('tr.add-row a, .add-row a, [data-inline-add], .d-inline-add');
        if (addBtn) {
            for (var i = 0; i < count; i++) {
                addBtn.click();
            }
        }
    }

    // -----------------------------------------------------------------
    // Form Serialization & State Management
    // -----------------------------------------------------------------
    function saveFormToState(index) {
        var form = document.getElementById('product_form');
        if (!form || !batchState.products[index]) return;

        var prod = batchState.products[index];
        var data = {};
        var elements = form.querySelectorAll('input:not([type="file"]), select, textarea');
        elements.forEach(function(el) {
            if (el.name && !el.name.startsWith('csrfmiddlewaretoken')) {
                if (el.type === 'checkbox') {
                    data[el.name] = el.checked;
                } else if (el.type === 'radio') {
                    if (el.checked) data[el.name] = el.value;
                } else {
                    data[el.name] = el.value;
                }
            }
        });
        prod.data = data;

        // Save files
        var fileInputs = form.querySelectorAll('input[type="file"]');
        fileInputs.forEach(function(finp) {
            if (finp.name && finp.files && finp.files.length > 0) {
                prod.files.set(finp.name, finp.files[0]);
            }
        });

        // 1. Capture Product Colors / Variants rows
        var variantRows = [];
        var vTotal = document.querySelector('#id_variant_items-TOTAL_FORMS');
        var vCount = vTotal ? parseInt(vTotal.value, 10) : 0;
        for (var i = 0; i < vCount; i++) {
            var colorInp = document.querySelector('#id_variant_items-' + i + '-color, [name="variant_items-' + i + '-color"]');
            var mainInp = document.querySelector('#id_variant_items-' + i + '-is_main, [name="variant_items-' + i + '-is_main"]');
            var urlInp = document.querySelector('#id_variant_items-' + i + '-image, [name="variant_items-' + i + '-image"]');
            var fileInp = document.querySelector('#id_variant_items-' + i + '-image_file, [name="variant_items-' + i + '-image_file"]');
            
            var fileObj = (fileInp && fileInp.files && fileInp.files[0]) || prod.files.get('variant_items-' + i + '-image_file') || null;

            variantRows.push({
                color: colorInp ? colorInp.value : '',
                is_main: mainInp ? mainInp.checked : false,
                image: urlInp ? urlInp.value : '',
                file: fileObj
            });
        }
        prod.variantRows = variantRows;

        // 2. Capture Gallery items rows
        var galleryRows = [];
        var gTotal = document.querySelector('#id_gallery_items-TOTAL_FORMS');
        var gCount = gTotal ? parseInt(gTotal.value, 10) : 0;
        for (var j = 0; j < gCount; j++) {
            var varSelect = document.querySelector('#id_gallery_items-' + j + '-variant, [name="gallery_items-' + j + '-variant"]');
            var gUrlInp = document.querySelector('#id_gallery_items-' + j + '-image, [name="gallery_items-' + j + '-image"]');
            var gFileInp = document.querySelector('#id_gallery_items-' + j + '-image_file, [name="gallery_items-' + j + '-image_file"]');

            var gFileObj = (gFileInp && gFileInp.files && gFileInp.files[0]) || prod.files.get('gallery_items-' + j + '-image_file') || null;

            galleryRows.push({
                variant: varSelect ? varSelect.value : '',
                image: gUrlInp ? gUrlInp.value : '',
                file: gFileObj
            });
        }
        prod.galleryRows = galleryRows;
    }

    function loadStateToForm(index) {
        var form = document.getElementById('product_form');
        if (!form || !batchState.products[index]) return;

        var prod = batchState.products[index];
        var data = prod.data || {};

        // Populate or clear basic fields
        var elements = form.querySelectorAll('input:not([type="file"]), select, textarea');
        elements.forEach(function(el) {
            if (el.name && !el.name.startsWith('csrfmiddlewaretoken') && el.name.indexOf('-') === -1) {
                if (data.hasOwnProperty(el.name)) {
                    if (el.type === 'checkbox') {
                        el.checked = Boolean(data[el.name]);
                    } else if (el.type === 'radio') {
                        el.checked = (el.value === data[el.name]);
                    } else {
                        el.value = data[el.name];
                    }
                } else {
                    if (el.type === 'checkbox') {
                        el.checked = false;
                    } else if (el.name === 'brand') {
                        el.value = 'Silk & Loom';
                    } else {
                        el.value = '';
                    }
                }
            }
        });

        // Sync global file cache to ONLY this product's files
        window._adminFileCache = new Map(prod.files);

        // Restore main image file if cached
        var mainFileInput = form.querySelector('#id_image_file, input[name="image_file"]');
        if (mainFileInput) {
            if (prod.files.has('image_file')) {
                try {
                    var dt = new DataTransfer();
                    dt.items.add(prod.files.get('image_file'));
                    mainFileInput.files = dt.files;
                } catch (e) {}
            } else {
                try { mainFileInput.value = ''; } catch (e) {}
                window._adminFileCache.delete('image_file');
            }
        }

        // 1. Clear all existing inlines (ensures 0 rows for empty products)
        clearInlineGroup('variant_items');
        clearInlineGroup('gallery_items');

        // 2. Restore variantRows if present
        var vRows = prod.variantRows || [];
        if (vRows.length > 0) {
            addInlineRows('variant_items', vRows.length);
            vRows.forEach(function(row, i) {
                var colorInp = document.querySelector('#id_variant_items-' + i + '-color, [name="variant_items-' + i + '-color"]');
                var mainInp = document.querySelector('#id_variant_items-' + i + '-is_main, [name="variant_items-' + i + '-is_main"]');
                var urlInp = document.querySelector('#id_variant_items-' + i + '-image, [name="variant_items-' + i + '-image"]');
                var fileInp = document.querySelector('#id_variant_items-' + i + '-image_file, [name="variant_items-' + i + '-image_file"]');

                if (colorInp) colorInp.value = row.color || '';
                if (mainInp) mainInp.checked = Boolean(row.is_main);
                if (urlInp) urlInp.value = row.image || '';
                if (fileInp && row.file) {
                    try {
                        var dt = new DataTransfer();
                        dt.items.add(row.file);
                        fileInp.files = dt.files;
                    } catch (e) {}
                }
            });
        }

        // 3. Sync variant options for gallery dropdowns
        if (typeof window.doSyncVariantOptions === 'function') {
            window.doSyncVariantOptions();
        }

        // 4. Restore galleryRows if present
        var gRows = prod.galleryRows || [];
        if (gRows.length > 0) {
            addInlineRows('gallery_items', gRows.length);
            gRows.forEach(function(row, j) {
                var varSelect = document.querySelector('#id_gallery_items-' + j + '-variant, [name="gallery_items-' + j + '-variant"]');
                var gUrlInp = document.querySelector('#id_gallery_items-' + j + '-image, [name="gallery_items-' + j + '-image"]');
                var gFileInp = document.querySelector('#id_gallery_items-' + j + '-image_file, [name="gallery_items-' + j + '-image_file"]');

                if (varSelect && row.variant) varSelect.value = row.variant;
                if (gUrlInp) gUrlInp.value = row.image || '';
                if (gFileInp && row.file) {
                    try {
                        var dt = new DataTransfer();
                        dt.items.add(row.file);
                        gFileInp.files = dt.files;
                    } catch (e) {}
                }
            });
        }

        // If product already saved, disable inputs
        var isSaved = Boolean(prod.saved);
        elements.forEach(function(el) {
            el.disabled = isSaved;
        });
        var allFileInputs = form.querySelectorAll('input[type="file"]');
        allFileInputs.forEach(function(el) {
            el.disabled = isSaved;
        });
    }

    function switchToProduct(targetIndex) {
        if (targetIndex === batchState.activeIndex) return;
        saveFormToState(batchState.activeIndex);
        batchState.activeIndex = targetIndex;
        loadStateToForm(targetIndex);
        renderTabs();
    }

    // -----------------------------------------------------------------
    // Copy Details from Source Product
    // -----------------------------------------------------------------
    function copyDetailsFromProduct(sourceIndex, targetIndex) {
        saveFormToState(batchState.activeIndex);
        var sourceProd = batchState.products[sourceIndex];
        var targetProd = batchState.products[targetIndex];
        if (!sourceProd || !targetProd) return;

        var sourceData = sourceProd.data || {};
        var fieldsToCopy = ['category', 'brand', 'description', 'is_new_arrival', 'new_arrival_order'];

        fieldsToCopy.forEach(function(f) {
            if (sourceData.hasOwnProperty(f)) {
                targetProd.data[f] = sourceData[f];
            }
        });

        loadStateToForm(targetIndex);
        renderTabs();

        // Highlight copied fields
        var form = document.getElementById('product_form');
        fieldsToCopy.forEach(function(fName) {
            var field = form.querySelector('[name="' + fName + '"]');
            if (field) {
                field.style.transition = 'all 0.3s ease';
                field.style.boxShadow = '0 0 0 3px rgba(16, 185, 129, 0.4)';
                field.style.borderColor = '#10b981';
                setTimeout(function() {
                    field.style.boxShadow = '';
                    field.style.borderColor = '';
                }, 1200);
            }
        });
    }

    // -----------------------------------------------------------------
    // Sequential Batch Save Runner with Real-Time Live Percentage
    // -----------------------------------------------------------------
    function executeBatchSave() {
        var form = document.getElementById('product_form');
        if (!form) return;

        // Save current active form state before starting
        saveFormToState(batchState.activeIndex);

        // Pre-validation: ensure all unsaved products have Name and Category
        for (var i = 0; i < batchState.products.length; i++) {
            var p = batchState.products[i];
            if (!p.saved) {
                var pName = (p.data['name'] || '').trim();
                var pCat = (p.data['category'] || '').trim();
                if (!pName || !pCat) {
                    switchToProduct(i);
                    alert('⚠️ ' + p.name + ' is missing required information (Product Name and Category). Please fill them before saving.');
                    var missingInp = form.querySelector(pName ? '[name="category"]' : '[name="name"]');
                    if (missingInp) {
                        missingInp.focus();
                        missingInp.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }
                    return;
                }
            }
        }

        // Create Live Progress Modal
        var modalId = 'batch-progress-modal';
        var oldModal = document.getElementById(modalId);
        if (oldModal) oldModal.remove();

        var modal = document.createElement('div');
        modal.id = modalId;
        modal.style.position = 'fixed';
        modal.style.inset = '0';
        modal.style.background = 'rgba(0, 0, 0, 0.6)';
        modal.style.backdropFilter = 'blur(10px)';
        modal.style.webkitBackdropFilter = 'blur(10px)';
        modal.style.zIndex = '999999999';
        modal.style.display = 'flex';
        modal.style.alignItems = 'center';
        modal.style.justifyContent = 'center';
        modal.style.padding = '20px';

        modal.innerHTML = `
            <div class="card bg-base-100 text-base-content border border-base-content/15 shadow-2xl max-w-lg w-full p-6 rounded-2xl space-y-4">
                <!-- Modal Header -->
                <div class="flex items-center gap-3">
                    <div id="batch-modal-radial" class="radial-progress text-primary font-bold text-xs transition-all duration-100" style="--value:0; --size:3.6rem; --thickness: 3.5px;" role="progressbar">
                        <span id="batch-modal-pct-text">0%</span>
                    </div>
                    <div>
                        <h3 class="text-sm font-bold text-base-content m-0">Saving Multi-Product Batch</h3>
                        <p id="batch-modal-subtitle" class="text-xs text-base-content/60 m-0">Uploading media & creating records...</p>
                    </div>
                </div>

                <!-- Products Step List with Live Percentage Progress -->
                <div class="space-y-2.5 max-h-64 overflow-y-auto p-1" id="batch-progress-list">
                    ${batchState.products.map(function(prod, idx) {
                        return `
                            <div id="batch-step-item-${idx}" class="p-3 rounded-xl border border-base-content/10 bg-base-200/50 flex flex-col gap-1.5 transition-all">
                                <div class="flex items-center justify-between text-xs">
                                    <span class="font-bold text-base-content">${idx + 1}. ${prod.data['name'] || prod.name}</span>
                                    <span id="batch-step-status-${idx}" class="badge badge-xs badge-neutral font-medium">Waiting</span>
                                </div>
                                <div class="w-full bg-base-300 rounded-full h-1.5 overflow-hidden">
                                    <div id="batch-step-bar-${idx}" class="bg-primary h-full transition-all duration-100 rounded-full" style="width: 0%;"></div>
                                </div>
                                <div class="flex justify-between items-center text-[11px] text-base-content/50 font-mono">
                                    <span id="batch-step-detail-${idx}">Ready</span>
                                    <span id="batch-step-bytes-${idx}">0.0 / 0.0 MB</span>
                                </div>
                            </div>
                        `;
                    }).join('')}
                </div>

                <!-- Footer Summary -->
                <div class="pt-2 border-t border-base-content/10 flex justify-between items-center text-xs">
                    <span id="batch-overall-summary" class="text-base-content/70">Processing 0 / ${batchState.products.length}...</span>
                </div>
            </div>
        `;
        document.body.appendChild(modal);

        // Run sequential save
        runSaveChain(0, function(allSuccess) {
            if (allSuccess) {
                var summaryEl = document.getElementById('batch-overall-summary');
                var subEl = document.getElementById('batch-modal-subtitle');
                if (summaryEl) summaryEl.innerHTML = '<span class="text-success font-bold">🎉 All ' + batchState.products.length + ' products saved! Redirecting to products list...</span>';
                if (subEl) subEl.textContent = 'Completed successfully!';
                setTimeout(function() {
                    window.location.href = '/admin/products/product/';
                }, 1200);
            }
        });
    }

    function runSaveChain(index, onComplete) {
        if (index >= batchState.products.length) {
            if (typeof onComplete === 'function') onComplete(true);
            return;
        }

        var prod = batchState.products[index];
        var itemStatus = document.getElementById('batch-step-status-' + index);
        var itemBar = document.getElementById('batch-step-bar-' + index);
        var itemDetail = document.getElementById('batch-step-detail-' + index);
        var itemBytes = document.getElementById('batch-step-bytes-' + index);
        var summaryEl = document.getElementById('batch-overall-summary');
        var modalRadial = document.getElementById('batch-modal-radial');
        var modalPctText = document.getElementById('batch-modal-pct-text');

        if (summaryEl) {
            summaryEl.textContent = 'Saving product ' + (index + 1) + ' of ' + batchState.products.length + ' (' + (prod.data['name'] || prod.name) + ')...';
        }

        if (prod.saved) {
            if (itemStatus) {
                itemStatus.className = 'badge badge-xs badge-success text-success-content';
                itemStatus.textContent = 'Already Saved ✓';
            }
            if (itemBar) itemBar.style.width = '100%';
            runSaveChain(index + 1, onComplete);
            return;
        }

        if (itemStatus) {
            itemStatus.className = 'badge badge-xs badge-primary text-primary-content';
            itemStatus.textContent = 'Saving...';
        }
        if (itemDetail) itemDetail.textContent = 'Preparing upload...';

        // Switch form to this product
        loadStateToForm(index);
        var form = document.getElementById('product_form');
        var formData = new FormData(form);
        formData.set('_save', 'Save');

        var postUrl = form.action || window.location.href;

        var xhr = new XMLHttpRequest();
        xhr.open('POST', postUrl, true);
        xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
        xhr.timeout = 180000; // 3 min safety timeout

        var progressTimer = null;
        var currentPct = 0;

        function setProductProgress(pct, detailText, byteText) {
            currentPct = Math.max(0, Math.min(100, pct));
            if (itemBar) itemBar.style.width = currentPct + '%';
            if (modalRadial) modalRadial.style.setProperty('--value', currentPct);
            if (modalPctText) modalPctText.textContent = currentPct + '%';
            if (detailText && itemDetail) itemDetail.textContent = detailText;
            if (byteText && itemBytes) itemBytes.textContent = byteText;
        }

        // Check if this product has files
        var hasFiles = Boolean(prod.files && prod.files.size > 0);
        var totalBytes = 0;
        if (hasFiles) {
            prod.files.forEach(function(file) {
                if (file && file.size) totalBytes += file.size;
            });
        }

        var startPct = hasFiles ? 8 : 18;
        setProductProgress(startPct, hasFiles ? 'Uploading media...' : 'Saving product data...', hasFiles ? '0.0 MB' : '');

        function startBatchProcessingTicker() {
            if (progressTimer) return;
            progressTimer = setInterval(function() {
                if (currentPct < 99) {
                    var step = currentPct < 60 ? 3.5 : (currentPct < 85 ? 1.8 : (currentPct < 94 ? 0.7 : (currentPct < 98 ? 0.2 : 0.05)));
                    currentPct = Math.min(99, currentPct + step);
                    var displayPct = Math.floor(currentPct);
                    var msg = displayPct < 60 ? 'Processing product data' : (displayPct < 85 ? 'Updating database records' : (displayPct < 95 ? 'Syncing with cloud storage' : 'Finalizing transaction'));
                    setProductProgress(
                        displayPct,
                        msg + ' (' + displayPct + '%)',
                        hasFiles && totalBytes > 0 ? (totalBytes / (1024 * 1024)).toFixed(1) + ' MB' : ''
                    );
                }
            }, 100);
        }

        // If no files to upload, start server ticker immediately
        if (!hasFiles) {
            startBatchProcessingTicker();
        }

        // Phase 1: Upload stream (8% -> 60%)
        xhr.upload.onprogress = function(event) {
            if (event.lengthComputable && event.total > 0 && hasFiles) {
                var rawPercent = (event.loaded / event.total);
                var scaledPercent = Math.max(8, Math.round(rawPercent * 60));
                currentPct = scaledPercent;
                var mbLoaded = (event.loaded / (1024 * 1024)).toFixed(1);
                var mbTotal = (event.total / (1024 * 1024)).toFixed(1);

                setProductProgress(
                    scaledPercent,
                    'Uploading media (' + Math.round(rawPercent * 100) + '%)...',
                    mbLoaded + ' / ' + mbTotal + ' MB'
                );
            }
        };

        // Phase 2: Upload finished -> Server & Supabase storage calculation
        xhr.upload.onload = function() {
            currentPct = Math.max(currentPct, 60);
            startBatchProcessingTicker();
        };

        // Fallback safety trigger
        setTimeout(function() {
            if (!progressTimer) {
                startBatchProcessingTicker();
            }
        }, 250);

        xhr.onload = function() {
            clearInterval(progressTimer);

            var responseHtml = xhr.responseText || '';
            var parser = new DOMParser();
            var doc = parser.parseFromString(responseHtml, 'text/html');

            var errorNote = doc.querySelector('.errornote, .alert-error, div.errors, ul.errorlist, .id-injected-error');

            var isSuccess = !errorNote && (xhr.status === 200 || xhr.status === 302);

            if (isSuccess) {
                // Phase 3: Complete to 100%
                setProductProgress(100, 'Saved successfully ✓', '100%');
                prod.saved = true;
                prod.hasError = false;

                if (itemStatus) {
                    itemStatus.className = 'badge badge-xs badge-success text-success-content';
                    itemStatus.textContent = 'Saved ✓';
                }

                renderTabs();

                setTimeout(function() {
                    runSaveChain(index + 1, onComplete);
                }, 350);
            } else {
                // Validation error occurred on this product!
                prod.saved = false;
                prod.hasError = true;
                if (itemStatus) {
                    itemStatus.className = 'badge badge-xs badge-error text-error-content';
                    itemStatus.textContent = 'Error ❌';
                }
                if (itemDetail) itemDetail.textContent = 'Validation error on server';

                // Close modal
                var modal = document.getElementById('batch-progress-modal');
                if (modal) modal.remove();

                // Switch to this failed product tab and map errors
                switchToProduct(index);

                // Map field errors into current DOM
                form.querySelectorAll('.errornote, .alert-error, div.errors, .id-injected-error').forEach(function(el) { el.remove(); });
                form.querySelectorAll('.errorlist, .text-error').forEach(function(el) { el.remove(); });

                if (errorNote) {
                    var importedNote = document.importNode(errorNote, true);
                    importedNote.classList.add('id-injected-error');
                    form.insertBefore(importedNote, form.firstChild);
                }

                var docRows = doc.querySelectorAll('div[class*="field-"], tr[class*="form-row"], .form-row, td[class*="field-"]');
                var firstErrorInp = null;
                docRows.forEach(function(row) {
                    var errs = row.querySelector('.errorlist, .text-error');
                    if (errs) {
                        var inp = row.querySelector('input, select, textarea');
                        if (inp && inp.id) {
                            var currentInp = form.querySelector('#' + CSS.escape(inp.id));
                            if (currentInp && currentInp.parentNode) {
                                var importedErr = document.importNode(errs, true);
                                importedErr.classList.add('id-injected-error');
                                currentInp.parentNode.insertBefore(importedErr, currentInp);
                                if (!firstErrorInp) firstErrorInp = currentInp;
                            }
                        }
                    }
                });

                if (firstErrorInp) {
                    firstErrorInp.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    try { firstErrorInp.focus(); } catch (e) {}
                }

                alert('⚠️ Saving paused: ' + (prod.data['name'] || prod.name) + ' has validation errors. Previously saved products are safe. Please fix the highlighted errors and click Save All again.');

                if (typeof onComplete === 'function') onComplete(false);
            }
        };

        xhr.ontimeout = function() {
            clearInterval(progressTimer);
            prod.hasError = true;
            if (itemStatus) {
                itemStatus.className = 'badge badge-xs badge-error text-error-content';
                itemStatus.textContent = 'Timeout ❌';
            }
            var modal = document.getElementById('batch-progress-modal');
            if (modal) modal.remove();
            switchToProduct(index);
            alert('⚠️ Upload timed out for ' + (prod.data['name'] || prod.name) + '. Please check your connection and retry.');
            if (typeof onComplete === 'function') onComplete(false);
        };

        xhr.onerror = function() {
            clearInterval(progressTimer);
            prod.hasError = true;
            if (itemStatus) {
                itemStatus.className = 'badge badge-xs badge-error text-error-content';
                itemStatus.textContent = 'Failed ❌';
            }
            var modal = document.getElementById('batch-progress-modal');
            if (modal) modal.remove();
            switchToProduct(index);
            alert('⚠️ Network or server error occurred while saving ' + (prod.data['name'] || prod.name) + '.');
            if (typeof onComplete === 'function') onComplete(false);
        };

        xhr.send(formData);
    }

    // -----------------------------------------------------------------
    // Initialization
    // -----------------------------------------------------------------
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initBatchCreator);
    } else {
        initBatchCreator();
    }
    setTimeout(initBatchCreator, 300);
})();
