(function() {
    'use strict';

    // Only run on the Product Change (Edit) page: /admin/products/product/<id>/change/
    var pathname = window.location.pathname;
    var changePageRegex = /\/admin\/products\/product\/([^\/]+)\/change\/?$/;
    var match = pathname.match(changePageRegex);
    if (!match) {
        return;
    }

    var currentProductId = decodeURIComponent(match[1]);

    // -----------------------------------------------------------------
    // Parse URL params for ?batch_ids=
    // -----------------------------------------------------------------
    var urlParams = new URLSearchParams(window.location.search);
    var rawBatchIds = urlParams.get('batch_ids');
    var initialIds = [];
    if (rawBatchIds) {
        initialIds = rawBatchIds.split(',').map(function(id) { return id.trim(); }).filter(Boolean);
    }
    if (initialIds.indexOf(currentProductId) === -1) {
        initialIds.unshift(currentProductId);
    }

    // -----------------------------------------------------------------
    // Batch Editor State
    // -----------------------------------------------------------------
    var editorState = {
        enabled: initialIds.length > 1 || rawBatchIds !== null,
        activeIndex: 0,
        products: []
    };

    // Initialize product list in state
    initialIds.forEach(function(pId, idx) {
        editorState.products.push({
            id: pId,
            name: 'Product ' + pId,
            loaded: idx === 0, // First product is already in the DOM
            modified: false,
            saved: false,
            hasError: false,
            errorMessage: null,
            formHtml: null,
            files: new Map(),
            data: {}
        });
    });

    // -----------------------------------------------------------------
    // Initialization
    // -----------------------------------------------------------------
    function initBatchEditor() {
        var form = document.getElementById('product_form');
        if (!form || form.dataset.batchEditorInitialized === 'true') return;
        form.dataset.batchEditorInitialized = 'true';

        // 1. Create Top Batch Editor Workspace Container
        var batchContainer = document.createElement('div');
        batchContainer.id = 'batch-product-editor-wrapper';
        batchContainer.className = 'w-full mb-6 transition-all duration-200';
        batchContainer.innerHTML = `
            <div class="card bg-base-100 border border-base-content/15 shadow-sm rounded-xl overflow-hidden">
                <!-- Top Toolbar Header -->
                <div class="p-4 bg-base-200/50 border-b border-base-content/10 flex flex-wrap items-center justify-between gap-3">
                    <div class="flex items-center gap-3">
                        <div class="w-9 h-9 rounded-lg bg-secondary/10 text-secondary flex items-center justify-center font-bold text-lg">
                            ⚡
                        </div>
                        <div>
                            <h3 class="text-sm font-bold text-base-content m-0">Multi-Product Batch Editor</h3>
                            <p class="text-xs text-base-content/60 m-0">Edit multiple existing products with tabbed switching, one-click copy & sequential batch saving</p>
                        </div>
                    </div>

                    <div class="flex items-center gap-3">
                        <!-- Batch Mode Toggle Button -->
                        <button type="button" id="btn-toggle-editor-mode" class="btn btn-sm ${editorState.enabled ? 'btn-secondary' : 'btn-outline border-base-content/20'} gap-2">
                            <span id="editor-mode-toggle-icon">${editorState.enabled ? '✓' : '⚡'}</span>
                            <span id="editor-mode-toggle-text">${editorState.enabled ? 'Batch Edit Mode Active' : 'Enable Batch Edit Mode'}</span>
                        </button>
                    </div>
                </div>

                <!-- Batch Management Body (Visible when Batch Mode is Active) -->
                <div id="editor-management-body" class="p-4 space-y-4" style="display: ${editorState.enabled ? 'block' : 'none'};">
                    <!-- Top Action Bar -->
                    <div class="flex flex-wrap items-center justify-between gap-4 pb-3 border-b border-base-content/10">
                        <!-- Add Product to Batch Input -->
                        <div class="flex items-center gap-2">
                            <span class="text-xs font-semibold text-base-content/70">Add Product to Batch:</span>
                            <div class="join">
                                <input type="text" id="input-add-product-id" placeholder="Enter Product ID (e.g. 1-2)" class="input input-xs input-bordered join-item w-48 text-xs font-mono" />
                                <button type="button" id="btn-add-product-to-batch" class="btn btn-xs btn-neutral join-item">Add</button>
                            </div>
                        </div>

                        <!-- Top Save All Button -->
                        <div class="flex items-center gap-2">
                            <button type="button" id="btn-editor-save-all-top" class="btn btn-sm btn-secondary gap-2 shadow-sm font-semibold">
                                <span>💾</span> Save All Products (<span class="editor-total-count">${editorState.products.length}</span>)
                            </button>
                        </div>
                    </div>

                    <!-- Product Tabs Bar -->
                    <div class="flex flex-wrap items-center gap-2" id="editor-tabs-bar">
                        <!-- Dynamic Product Tabs injected here -->
                    </div>

                    <!-- Quick Fill Bar (Shown on tab 2 and higher) -->
                    <div id="editor-copy-bar" class="p-3 bg-secondary/5 border border-secondary/20 rounded-lg flex flex-wrap items-center justify-between gap-3" style="display: none;">
                        <div class="flex items-center gap-2">
                            <span class="text-secondary text-sm">📋</span>
                            <span class="text-xs text-base-content/80 font-medium">Quick Fill: Copy Category, Brand, Description, and New Arrival settings from Product 1.</span>
                        </div>
                        <button type="button" id="btn-editor-copy-from-first" class="btn btn-xs btn-secondary btn-outline font-semibold gap-1">
                            <span>📋</span> Copy from Tab 1
                        </button>
                    </div>

                    <!-- Active Product Status Banner -->
                    <div id="editor-active-status-banner" class="text-xs py-1 px-3 rounded bg-base-200/60 text-base-content/70 flex items-center justify-between">
                        <span>Currently Editing: <strong id="editor-active-label" class="text-secondary">${currentProductId}</strong></span>
                        <span id="editor-active-status-badge" class="badge badge-xs badge-neutral">Loaded</span>
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
            bottomSaveAll.id = 'btn-editor-save-all-bottom';
            bottomSaveAll.className = 'btn btn-secondary gap-2 font-bold shadow-md';
            bottomSaveAll.style.display = editorState.enabled ? 'inline-flex' : 'none';
            bottomSaveAll.innerHTML = '<span>💾</span> Save All Products (<span class="editor-total-count">' + editorState.products.length + '</span>)';
            submitRow.insertBefore(bottomSaveAll, submitRow.firstChild);
        }

        // 3. Attach Event Listeners
        var toggleBtn = document.getElementById('btn-toggle-editor-mode');
        var editorBody = document.getElementById('editor-management-body');
        var addProdBtn = document.getElementById('btn-add-product-to-batch');
        var addProdInput = document.getElementById('input-add-product-id');
        var copyBtn = document.getElementById('btn-editor-copy-from-first');
        var saveAllTop = document.getElementById('btn-editor-save-all-top');
        var saveAllBottom = document.getElementById('btn-editor-save-all-bottom');

        toggleBtn.addEventListener('click', function() {
            editorState.enabled = !editorState.enabled;
            if (editorState.enabled) {
                editorBody.style.display = 'block';
                toggleBtn.classList.add('btn-secondary');
                toggleBtn.classList.remove('btn-outline');
                document.getElementById('editor-mode-toggle-icon').textContent = '✓';
                document.getElementById('editor-mode-toggle-text').textContent = 'Batch Edit Mode Active';
                if (saveAllBottom) saveAllBottom.style.display = 'inline-flex';
                renderTabs();
            } else {
                editorBody.style.display = 'none';
                toggleBtn.classList.remove('btn-secondary');
                toggleBtn.classList.add('btn-outline');
                document.getElementById('editor-mode-toggle-icon').textContent = '⚡';
                document.getElementById('editor-mode-toggle-text').textContent = 'Enable Batch Edit Mode';
                if (saveAllBottom) saveAllBottom.style.display = 'none';
            }
        });

        addProdBtn.addEventListener('click', function() {
            var val = addProdInput.value.trim();
            if (!val) return;
            addProductToBatch(val);
            addProdInput.value = '';
        });

        addProdInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                addProdBtn.click();
            }
        });

        copyBtn.addEventListener('click', function() {
            copyDetailsFromProduct(0, editorState.activeIndex);
        });

        if (saveAllTop) saveAllTop.addEventListener('click', executeBatchSave);
        if (saveAllBottom) saveAllBottom.addEventListener('click', executeBatchSave);

        // Capture initial product name from form
        var nameInput = form.querySelector('#id_name, input[name="name"]');
        if (nameInput && editorState.products[0]) {
            editorState.products[0].name = nameInput.value || ('Product ' + currentProductId);
        }

        // Track user edits on form
        form.addEventListener('input', function() {
            if (editorState.products[editorState.activeIndex]) {
                editorState.products[editorState.activeIndex].modified = true;
                renderTabs();
            }
        });

        renderTabs();
    }

    // -----------------------------------------------------------------
    // Add Product to Batch
    // -----------------------------------------------------------------
    function addProductToBatch(productId) {
        var exists = editorState.products.some(function(p) { return p.id === productId; });
        if (exists) {
            alert('Product ' + productId + ' is already in the batch tabs.');
            return;
        }

        if (editorState.products.length >= 10) {
            alert('Maximum 10 products can be edited in one batch session.');
            return;
        }

        var newIdx = editorState.products.length;
        editorState.products.push({
            id: productId,
            name: 'Product ' + productId,
            loaded: false,
            modified: false,
            saved: false,
            hasError: false,
            errorMessage: null,
            formHtml: null,
            files: new Map(),
            data: {}
        });

        renderTabs();
        switchToProduct(newIdx);
    }

    // -----------------------------------------------------------------
    // Render Tabs
    // -----------------------------------------------------------------
    function renderTabs() {
        var count = editorState.products.length;
        document.querySelectorAll('.editor-total-count').forEach(function(el) { el.textContent = count; });

        var tabsBar = document.getElementById('editor-tabs-bar');
        if (!tabsBar) return;
        tabsBar.innerHTML = '';

        editorState.products.forEach(function(prod, idx) {
            var isActive = idx === editorState.activeIndex;
            var tabBtn = document.createElement('button');
            tabBtn.type = 'button';
            tabBtn.className = 'btn btn-sm ' + (isActive ? 'btn-secondary shadow-sm' : 'btn-outline border-base-content/20 bg-base-100') + ' gap-2 transition-all';
            
            var badgeClass = 'badge-neutral';
            var badgeText = 'Loaded';
            if (prod.saved) {
                badgeClass = 'badge-success text-success-content';
                badgeText = 'Saved ✓';
            } else if (prod.hasError) {
                badgeClass = 'badge-error text-error-content';
                badgeText = 'Error ⚠️';
            } else if (prod.modified) {
                badgeClass = 'badge-warning text-warning-content';
                badgeText = 'Modified ✏️';
            } else if (!prod.loaded) {
                badgeClass = 'badge-ghost';
                badgeText = 'Pending ⏳';
            }

            tabBtn.innerHTML = `
                <span>${prod.saved ? '✓' : ('#' + prod.id)}</span>
                <span class="font-bold max-w-[150px] truncate">${prod.name}</span>
                <span class="badge badge-xs ${badgeClass}">${badgeText}</span>
            `;

            tabBtn.addEventListener('click', function() {
                switchToProduct(idx);
            });

            tabsBar.appendChild(tabBtn);
        });

        // Update Copy Bar visibility
        var copyBar = document.getElementById('editor-copy-bar');
        if (copyBar) {
            copyBar.style.display = editorState.activeIndex > 0 ? 'flex' : 'none';
        }

        // Update Active Status Banner
        var activeProd = editorState.products[editorState.activeIndex];
        if (activeProd) {
            document.getElementById('editor-active-label').textContent = '#' + activeProd.id + ' — ' + activeProd.name;
            var statusBadge = document.getElementById('editor-active-status-badge');
            if (activeProd.saved) {
                statusBadge.className = 'badge badge-xs badge-success text-success-content';
                statusBadge.textContent = 'Saved ✓';
            } else if (activeProd.hasError) {
                statusBadge.className = 'badge badge-xs badge-error text-error-content';
                statusBadge.textContent = 'Error: ' + (activeProd.errorMessage || 'Check fields');
            } else if (activeProd.modified) {
                statusBadge.className = 'badge badge-xs badge-warning text-warning-content';
                statusBadge.textContent = 'Modified (Unsaved)';
            } else {
                statusBadge.className = 'badge badge-xs badge-neutral';
                statusBadge.textContent = 'Loaded from Database';
            }
        }
    }

    // -----------------------------------------------------------------
    // Save Current Form State & Switch Tab
    // -----------------------------------------------------------------
    function saveCurrentFormToState() {
        var form = document.getElementById('product_form');
        var curr = editorState.products[editorState.activeIndex];
        if (!form || !curr) return;

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
        curr.data = data;
        curr.name = data['name'] || curr.name;

        // Save uploaded files
        var fileInputs = form.querySelectorAll('input[type="file"]');
        fileInputs.forEach(function(finp) {
            if (finp.name && finp.files && finp.files.length > 0) {
                curr.files.set(finp.name, finp.files[0]);
            }
        });

        // Clone current HTML snapshot
        curr.formHtml = form.innerHTML;
    }

    function switchToProduct(newIndex) {
        if (newIndex === editorState.activeIndex && editorState.products[newIndex].loaded) {
            return;
        }

        // Save current active form
        saveCurrentFormToState();

        editorState.activeIndex = newIndex;
        var targetProd = editorState.products[newIndex];
        var form = document.getElementById('product_form');

        if (!targetProd.loaded) {
            // Fetch HTML of target product change page
            fetchProductChangePage(targetProd, function(success) {
                if (success) {
                    renderTabs();
                }
            });
        } else {
            // Restore from cached HTML/State
            if (targetProd.formHtml) {
                form.innerHTML = targetProd.formHtml;
                restoreFilesToForm(targetProd, form);
                reinitializeAdminBehaviors(form);
            }
            renderTabs();
        }
    }

    // -----------------------------------------------------------------
    // Fetch Product Form HTML Asynchronously
    // -----------------------------------------------------------------
    function fetchProductChangePage(prod, callback) {
        var form = document.getElementById('product_form');
        var fetchUrl = '/admin/products/product/' + encodeURIComponent(prod.id) + '/change/';

        // Show loading indicator
        var loader = document.createElement('div');
        loader.id = 'batch-editor-loading-overlay';
        loader.className = 'p-8 text-center bg-base-100/90 rounded-xl border border-base-content/10 my-4';
        loader.innerHTML = `
            <div class="loading loading-spinner loading-md text-secondary mb-2"></div>
            <p class="text-sm font-semibold text-base-content">Loading Product #${prod.id} from Database...</p>
        `;
        form.style.opacity = '0.3';
        form.parentNode.insertBefore(loader, form);

        fetch(fetchUrl, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
        .then(function(res) {
            if (!res.ok) throw new Error('Product not found or server error (Status: ' + res.status + ')');
            return res.text();
        })
        .then(function(htmlText) {
            loader.remove();
            form.style.opacity = '1';

            var parser = new DOMParser();
            var doc = parser.parseFromString(htmlText, 'text/html');
            var remoteForm = doc.getElementById('product_form');

            if (!remoteForm) {
                throw new Error('Could not parse product form from server response.');
            }

            prod.formHtml = remoteForm.innerHTML;
            prod.loaded = true;

            // Extract initial name
            var nameInp = remoteForm.querySelector('#id_name, input[name="name"]');
            if (nameInp && nameInp.value) {
                prod.name = nameInp.value;
            }

            // Replace live form HTML
            form.innerHTML = prod.formHtml;
            form.action = fetchUrl;

            reinitializeAdminBehaviors(form);
            if (callback) callback(true);
        })
        .catch(function(err) {
            loader.remove();
            form.style.opacity = '1';
            prod.hasError = true;
            prod.errorMessage = err.message;
            alert('Error loading Product #' + prod.id + ': ' + err.message);
            if (callback) callback(false);
        });
    }

    // -----------------------------------------------------------------
    // Reinitialize Admin Scripts / Dropdowns on Swapped Form
    // -----------------------------------------------------------------
    function reinitializeAdminBehaviors(form) {
        // Re-trigger dynamic variant color synchronizers if available
        if (window._syncVariantDropdowns) {
            try { window._syncVariantDropdowns(); } catch (e) {}
        }
        // Re-attach bottom save button if removed by innerHTML swap
        var submitRow = form.querySelector('.submit-row');
        if (submitRow && !document.getElementById('btn-editor-save-all-bottom')) {
            var bottomSaveAll = document.createElement('button');
            bottomSaveAll.type = 'button';
            bottomSaveAll.id = 'btn-editor-save-all-bottom';
            bottomSaveAll.className = 'btn btn-secondary gap-2 font-bold shadow-md';
            bottomSaveAll.style.display = editorState.enabled ? 'inline-flex' : 'none';
            bottomSaveAll.innerHTML = '<span>💾</span> Save All Products (<span class="editor-total-count">' + editorState.products.length + '</span>)';
            bottomSaveAll.addEventListener('click', executeBatchSave);
            submitRow.insertBefore(bottomSaveAll, submitRow.firstChild);
        }
    }

    function restoreFilesToForm(prod, form) {
        if (!prod.files || prod.files.size === 0) return;
        prod.files.forEach(function(fileObj, inputName) {
            var finp = form.querySelector('input[type="file"][name="' + inputName + '"]');
            if (finp && fileObj) {
                try {
                    var dt = new DataTransfer();
                    dt.items.add(fileObj);
                    finp.files = dt.files;
                } catch (e) {}
            }
        });
    }

    // -----------------------------------------------------------------
    // Quick Copy from Tab 1 to Target Tab
    // -----------------------------------------------------------------
    function copyDetailsFromProduct(srcIdx, destIdx) {
        var src = editorState.products[srcIdx];
        var dest = editorState.products[destIdx];
        if (!src || !dest) return;

        // Ensure source state is fresh
        if (srcIdx === editorState.activeIndex) {
            saveCurrentFormToState();
        }

        var form = document.getElementById('product_form');
        var fieldsToCopy = ['category', 'brand', 'description', 'is_new_arrival', 'new_arrival_order'];
        var copiedCount = 0;

        fieldsToCopy.forEach(function(fieldName) {
            var val = src.data[fieldName];
            if (val !== undefined) {
                var el = form.querySelector('[name="' + fieldName + '"]');
                if (el) {
                    if (el.type === 'checkbox') {
                        el.checked = Boolean(val);
                    } else {
                        el.value = val;
                    }
                    copiedCount++;
                }
                dest.data[fieldName] = val;
            }
        });

        dest.modified = true;
        renderTabs();

        // Flash copy notification
        var copyBar = document.getElementById('editor-copy-bar');
        if (copyBar) {
            copyBar.classList.add('bg-success/10', 'border-success/30');
            setTimeout(function() {
                copyBar.classList.remove('bg-success/10', 'border-success/30');
            }, 1000);
        }
    }

    // -----------------------------------------------------------------
    // Sequential Batch Save Execution
    // -----------------------------------------------------------------
    function executeBatchSave() {
        saveCurrentFormToState();

        var total = editorState.products.length;
        if (total === 0) return;

        // Create Modal Progress Overlay
        var modal = document.createElement('div');
        modal.id = 'batch-save-progress-modal';
        modal.className = 'fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4';
        modal.innerHTML = `
            <div class="card bg-base-100 shadow-2xl border border-base-content/15 max-w-md w-full p-6 space-y-4">
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-full bg-secondary/15 text-secondary flex items-center justify-center font-bold text-lg animate-pulse">
                        💾
                    </div>
                    <div>
                        <h4 class="font-bold text-base text-base-content">Saving Products Batch</h4>
                        <p class="text-xs text-base-content/60" id="batch-save-status-text">Starting sequential update...</p>
                    </div>
                </div>

                <!-- Progress Bar -->
                <div class="w-full bg-base-200 rounded-full h-3 overflow-hidden border border-base-content/10">
                    <div id="batch-save-progress-bar" class="bg-secondary h-3 transition-all duration-300" style="width: 0%;"></div>
                </div>

                <div class="text-xs font-semibold text-base-content/70 flex justify-between">
                    <span id="batch-save-counter">Processing 0 / ${total}</span>
                    <span id="batch-save-percentage">0%</span>
                </div>

                <!-- Step Details -->
                <div id="batch-save-steps" class="max-h-40 overflow-y-auto space-y-1 text-xs border border-base-content/10 p-3 rounded-lg bg-base-200/40">
                </div>

                <!-- Close / Finish Button -->
                <div id="batch-save-footer" class="pt-2 flex justify-end" style="display: none;">
                    <button type="button" id="btn-batch-save-finish" class="btn btn-sm btn-secondary font-bold">Done & View Catalog</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);

        var currentIdx = 0;
        var successCount = 0;
        var errorCount = 0;

        function processNext() {
            if (currentIdx >= total) {
                // Completed
                document.getElementById('batch-save-status-text').textContent = 'Batch update complete!';
                document.getElementById('batch-save-footer').style.display = 'flex';
                document.getElementById('btn-batch-save-finish').addEventListener('click', function() {
                    window.location.href = '/admin/products/product/';
                });
                return;
            }

            var prod = editorState.products[currentIdx];
            var stepItem = document.createElement('div');
            stepItem.className = 'flex items-center justify-between py-0.5 text-base-content/80';
            stepItem.innerHTML = `<span>#${prod.id}: ${prod.name}</span> <span class="badge badge-xs badge-neutral">Updating...</span>`;
            document.getElementById('batch-save-steps').appendChild(stepItem);

            // Update Progress Bar
            var percent = Math.round(((currentIdx) / total) * 100);
            document.getElementById('batch-save-progress-bar').style.width = percent + '%';
            document.getElementById('batch-save-percentage').textContent = percent + '%';
            document.getElementById('batch-save-counter').textContent = `Processing ${currentIdx + 1} / ${total}`;

            // Build FormData
            var saveUrl = '/admin/products/product/' + encodeURIComponent(prod.id) + '/change/';
            var formData = new FormData();

            // Append CSRF Token
            var csrfToken = (document.querySelector('[name=csrfmiddlewaretoken]') || {}).value;
            if (csrfToken) {
                formData.append('csrfmiddlewaretoken', csrfToken);
            }
            formData.append('_continue', '1'); // Keeps on change page

            // Append all fields from state
            for (var key in prod.data) {
                if (prod.data.hasOwnProperty(key)) {
                    if (typeof prod.data[key] === 'boolean') {
                        if (prod.data[key]) formData.append(key, 'on');
                    } else {
                        formData.append(key, prod.data[key]);
                    }
                }
            }

            // Append files
            prod.files.forEach(function(fileObj, fieldName) {
                if (fileObj) {
                    formData.append(fieldName, fileObj);
                }
            });

            // Submit POST
            fetch(saveUrl, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(function(response) {
                if (response.ok) {
                    prod.saved = true;
                    prod.modified = false;
                    prod.hasError = false;
                    successCount++;
                    stepItem.querySelector('.badge').className = 'badge badge-xs badge-success text-success-content';
                    stepItem.querySelector('.badge').textContent = 'Saved ✓';
                } else {
                    throw new Error('HTTP ' + response.status);
                }
            })
            .catch(function(err) {
                prod.hasError = true;
                prod.errorMessage = err.message;
                errorCount++;
                stepItem.querySelector('.badge').className = 'badge badge-xs badge-error text-error-content';
                stepItem.querySelector('.badge').textContent = 'Error ⚠️';
            })
            .finally(function() {
                currentIdx++;
                var finalPercent = Math.round((currentIdx / total) * 100);
                document.getElementById('batch-save-progress-bar').style.width = finalPercent + '%';
                document.getElementById('batch-save-percentage').textContent = finalPercent + '%';
                renderTabs();
                processNext();
            });
        }

        processNext();
    }

    // -----------------------------------------------------------------
    // Boot on DOM Ready
    // -----------------------------------------------------------------
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initBatchEditor);
    } else {
        initBatchEditor();
    }
})();
