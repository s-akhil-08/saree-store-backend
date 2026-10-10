(function() {
    'use strict';

    // -------------------------------------------------------------
    // Helper: Collect all colors typed in Product Variants section
    // -------------------------------------------------------------
    function getAboveColors() {
        var colors = [];
        var inputs = document.querySelectorAll('input[id*="variant_items"][id$="-color"], input[name*="variant_items"][name$="color"]');
        inputs.forEach(function(inp) {
            var val = (inp.value || '').trim();
            if (val && colors.indexOf(val) === -1) {
                colors.push(val);
            }
        });
        return colors;
    }

    // -------------------------------------------------------------
    // Sync Variant dropdown options in Gallery rows
    // -------------------------------------------------------------
    function doSyncVariantOptions(btn) {
        if (btn) {
            var oldText = btn.innerHTML;
            btn.innerHTML = '⏳ Syncing...';
            setTimeout(function() {
                btn.innerHTML = oldText;
            }, 350);
        }
        var colors = getAboveColors();
        var selects = document.querySelectorAll('select[id*="gallery_items"][id*="variant"], select[name*="gallery_items"][name*="variant"]');

        selects.forEach(function(select) {
            var currentSelectedVal = select.value;
            var currentSelectedText = select.options[select.selectedIndex] ? select.options[select.selectedIndex].text : '';

            var existingOptions = [];
            for (var i = 0; i < select.options.length; i++) {
                var opt = select.options[i];
                if (opt.value && !opt.value.startsWith('COLOR:')) {
                    existingOptions.push({ value: opt.value, text: opt.text });
                }
            }

            colors.forEach(function(colorName) {
                var alreadyPresent = existingOptions.some(function(item) {
                    return item.text.toLowerCase().indexOf(colorName.toLowerCase()) !== -1;
                });
                if (!alreadyPresent) {
                    existingOptions.push({ value: 'COLOR:' + colorName, text: colorName });
                }
            });

            select.innerHTML = '';

            var defaultOpt = document.createElement('option');
            defaultOpt.value = '';
            defaultOpt.text = '-- Main Product Gallery --';
            select.appendChild(defaultOpt);

            existingOptions.forEach(function(item) {
                var opt = document.createElement('option');
                opt.value = item.value;
                opt.text = item.text;
                select.appendChild(opt);
            });

            if (currentSelectedVal) {
                select.value = currentSelectedVal;
            } else if (currentSelectedText && currentSelectedText !== '-- Main Product Gallery --') {
                for (var k = 0; k < select.options.length; k++) {
                    if (select.options[k].text === currentSelectedText) {
                        select.selectedIndex = k;
                        break;
                    }
                }
            }
        });

        updateBulkAddColorSelect();
    }
    window.doSyncVariantOptions = doSyncVariantOptions;

    // -------------------------------------------------------------
    // Update options in the Bulk Add Toolbar Color Dropdown
    // -------------------------------------------------------------
    function updateBulkAddColorSelect() {
        var bulkSelect = document.getElementById('bulk-color-select');
        if (!bulkSelect) return;

        var currentVal = bulkSelect.value;
        var colors = getAboveColors();

        bulkSelect.innerHTML = '<option value="">-- Main Product Gallery --</option>';
        colors.forEach(function(c) {
            var opt = document.createElement('option');
            opt.value = 'COLOR:' + c;
            opt.textContent = '🎨 ' + c;
            bulkSelect.appendChild(opt);
        });

        if (currentVal) {
            bulkSelect.value = currentVal;
        }
    }

    // -------------------------------------------------------------
    // 1. Bulk Add Gallery Rows
    // -------------------------------------------------------------
    function bulkAddGalleryRows(colorValue, count) {
        var galleryGroup = document.querySelector('#gallery_items-group, div[id*="gallery_items"]');
        if (!galleryGroup) return;

        var addRowLink = galleryGroup.querySelector('tr.add-row a, .add-row a, [data-inline-add], .d-inline-add');
        if (!addRowLink) {
            alert('Could not find the "Add another" button for gallery uploads.');
            return;
        }

        var totalFormsInput = document.querySelector('#id_gallery_items-TOTAL_FORMS');
        var initialTotal = totalFormsInput ? parseInt(totalFormsInput.value, 10) : document.querySelectorAll('tr[id^="gallery_items-"]').length;

        // Add N rows
        for (var i = 0; i < count; i++) {
            addRowLink.click();
        }

        doSyncVariantOptions();

        var newTotal = totalFormsInput ? parseInt(totalFormsInput.value, 10) : initialTotal + count;
        for (var idx = initialTotal; idx < newTotal; idx++) {
            var select = document.querySelector('#id_gallery_items-' + idx + '-variant, select[name="gallery_items-' + idx + '-variant"]');
            if (select && colorValue) {
                select.value = colorValue;
            }
        }

        var label = colorValue ? colorValue.replace('COLOR:', '') : 'Main Gallery';
        showToastNotification('✓ Added ' + count + ' gallery row' + (count > 1 ? 's' : '') + ' for "' + label + '" (Total: ' + newTotal + ' rows)');
    }

    // -------------------------------------------------------------
    // 2. Bulk Add Product Variant / Color Rows
    // -------------------------------------------------------------
    function bulkAddVariantRows(count) {
        var variantGroup = document.querySelector('#variant_items-group, div[id*="variant_items"]');
        if (!variantGroup) return;

        var addRowLink = variantGroup.querySelector('tr.add-row a, .add-row a, [data-inline-add], .d-inline-add');
        if (!addRowLink) {
            alert('Could not find the "Add another" button for variant colors.');
            return;
        }

        var totalFormsInput = document.querySelector('#id_variant_items-TOTAL_FORMS');
        var initialTotal = totalFormsInput ? parseInt(totalFormsInput.value, 10) : document.querySelectorAll('tr[id^="variant_items-"]').length;

        for (var i = 0; i < count; i++) {
            addRowLink.click();
        }

        var newTotal = totalFormsInput ? parseInt(totalFormsInput.value, 10) : initialTotal + count;
        showToastNotification('✓ Added ' + count + ' color variant row' + (count > 1 ? 's' : '') + ' (Total: ' + newTotal + ' rows)');
    }

    // -------------------------------------------------------------
    // Toast Notification Banner (Theme-Matched)
    // -------------------------------------------------------------
    function showToastNotification(text) {
        var existingToast = document.getElementById('admin-bulk-toast');
        if (existingToast) existingToast.remove();

        var toast = document.createElement('div');
        toast.id = 'admin-bulk-toast';
        toast.textContent = text;
        toast.style.position = 'fixed';
        toast.style.bottom = '24px';
        toast.style.right = '24px';
        toast.style.backgroundColor = 'hsl(var(--su, 142 76% 36%))';
        toast.style.color = 'hsl(var(--suc, 0 0% 100%))';
        toast.style.padding = '10px 18px';
        toast.style.borderRadius = '8px';
        toast.style.boxShadow = '0 4px 14px rgba(0,0,0,0.25)';
        toast.style.fontSize = '13px';
        toast.style.fontWeight = '600';
        toast.style.zIndex = '99999';
        toast.style.transition = 'all 0.3s ease';

        document.body.appendChild(toast);
        setTimeout(function() {
            toast.style.opacity = '0';
            setTimeout(function() { toast.remove(); }, 300);
        }, 3000);
    }

    // -------------------------------------------------------------
    // Helper: Setup Stepper Buttons (+ / -)
    // -------------------------------------------------------------
    function setupStepperEvents(container) {
        container.querySelectorAll('.stepper-btn').forEach(function(btn) {
            btn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                var targetId = btn.getAttribute('data-target');
                var input = container.querySelector('#' + targetId);
                if (!input) return;
                var currentVal = parseInt(input.value, 10) || 1;
                var action = btn.getAttribute('data-action');
                var isPlus = action === 'increase' || btn.classList.contains('stepper-btn-plus') || btn.textContent.trim() === '+';
                var min = parseInt(input.min, 10) || 1;
                var max = parseInt(input.max, 10) || 50;

                if (isPlus) {
                    if (currentVal < max) {
                        input.value = currentVal + 1;
                    }
                } else {
                    if (currentVal > min) {
                        input.value = currentVal - 1;
                    }
                }
                input.dispatchEvent(new Event('input', { bubbles: true }));
                input.dispatchEvent(new Event('change', { bubbles: true }));
            });
        });
    }

    // -------------------------------------------------------------
    // Attach Toolbars to Upper Side / Header (Theme Adaptive & Responsive)
    // -------------------------------------------------------------
    function attachToolbars() {
        // --- A. Gallery Bulk Add Toolbar ---
        var galleryGroup = document.querySelector('#gallery_items-group, div[id*="gallery_items"]');
        if (galleryGroup && !galleryGroup.querySelector('#bulk-add-gallery-container')) {
            var gHeader = galleryGroup.querySelector('h2, .collapse-title, legend');
            
            var toolbar = document.createElement('div');
            toolbar.id = 'bulk-add-gallery-container';
            toolbar.className = 'bulk-toolbar-card card bg-base-200 border border-base-content/20 text-base-content shadow-sm p-2 rounded-box';

            // Prevent collapsing the accordion when interacting with toolbar elements
            toolbar.addEventListener('click', function(e) { e.stopPropagation(); });
            toolbar.addEventListener('mousedown', function(e) { e.stopPropagation(); });
            toolbar.addEventListener('change', function(e) { e.stopPropagation(); });

            toolbar.innerHTML = `
                <div class="toolbar-badge text-primary font-bold text-xs">
                    <span>⚡ BULK ADD GALLERY:</span>
                </div>
                <div class="toolbar-controls flex flex-wrap items-center gap-2">
                    <select id="bulk-color-select" class="select select-bordered select-sm bg-base-100 text-base-content">
                        <option value="">-- Main Product Gallery --</option>
                    </select>
                    <div class="flex items-center gap-1">
                        <div class="bulk-stepper-group join border border-base-content/20 bg-base-100 rounded-btn">
                            <button type="button" class="stepper-btn stepper-btn-minus btn btn-xs join-item" data-target="bulk-gallery-count" data-action="decrease" title="Decrease">−</button>
                            <input type="number" id="bulk-gallery-count" class="input input-xs join-item w-10 text-center font-bold bg-transparent border-0 text-base-content" min="1" max="50" value="5" />
                            <button type="button" class="stepper-btn stepper-btn-plus btn btn-xs join-item" data-target="bulk-gallery-count" data-action="increase" title="Increase">+</button>
                        </div>
                        <span class="text-xs opacity-75 font-medium">rows</span>
                    </div>
                    <button type="button" id="btn-bulk-add-gallery" class="btn btn-primary btn-sm">
                        + Add Rows
                    </button>
                    <button type="button" id="btn-sync-variants-quick" class="btn btn-outline btn-sm">
                        🔄 Sync Colors
                    </button>
                </div>
            `;

            if (gHeader) {
                gHeader.appendChild(toolbar);
            } else {
                galleryGroup.prepend(toolbar);
            }

            setupStepperEvents(toolbar);

            // Click Handlers
            var btnAdd = toolbar.querySelector('#btn-bulk-add-gallery');
            if (btnAdd) {
                btnAdd.addEventListener('click', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    var colorVal = toolbar.querySelector('#bulk-color-select').value;
                    var count = parseInt(toolbar.querySelector('#bulk-gallery-count').value, 10) || 1;
                    bulkAddGalleryRows(colorVal, count);
                });
            }

            var btnSync = toolbar.querySelector('#btn-sync-variants-quick');
            if (btnSync) {
                btnSync.addEventListener('click', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    doSyncVariantOptions(btnSync);
                });
            }

            updateBulkAddColorSelect();
        }

        // --- B. Product Colors / Variants Bulk Add Toolbar ---
        var variantGroup = document.querySelector('#variant_items-group, div[id*="variant_items"]');
        if (variantGroup && !variantGroup.querySelector('#bulk-add-variant-container')) {
            var vHeader = variantGroup.querySelector('h2, .collapse-title, legend');

            var vToolbar = document.createElement('div');
            vToolbar.id = 'bulk-add-variant-container';
            vToolbar.className = 'bulk-toolbar-card card bg-base-200 border border-base-content/20 text-base-content shadow-sm p-2 rounded-box';

            // Prevent collapsing the accordion when interacting with toolbar elements
            vToolbar.addEventListener('click', function(e) { e.stopPropagation(); });
            vToolbar.addEventListener('mousedown', function(e) { e.stopPropagation(); });
            vToolbar.addEventListener('change', function(e) { e.stopPropagation(); });

            vToolbar.innerHTML = `
                <div class="toolbar-badge text-primary font-bold text-xs">
                    <span>⚡ BULK ADD COLORS:</span>
                </div>
                <div class="toolbar-controls flex flex-wrap items-center gap-2">
                    <div class="flex items-center gap-1">
                        <div class="bulk-stepper-group join border border-base-content/20 bg-base-100 rounded-btn">
                            <button type="button" class="stepper-btn stepper-btn-minus btn btn-xs join-item" data-target="bulk-variant-count" data-action="decrease" title="Decrease">−</button>
                            <input type="number" id="bulk-variant-count" class="input input-xs join-item w-10 text-center font-bold bg-transparent border-0 text-base-content" min="1" max="50" value="4" />
                            <button type="button" class="stepper-btn stepper-btn-plus btn btn-xs join-item" data-target="bulk-variant-count" data-action="increase" title="Increase">+</button>
                        </div>
                        <span class="text-xs opacity-75 font-medium">colors</span>
                    </div>
                    <button type="button" id="btn-bulk-add-variants" class="btn btn-primary btn-sm">
                        + Add Color Rows
                    </button>
                </div>
            `;

            if (vHeader) {
                vHeader.appendChild(vToolbar);
            } else {
                variantGroup.prepend(vToolbar);
            }

            setupStepperEvents(vToolbar);

            var btnAddV = vToolbar.querySelector('#btn-bulk-add-variants');
            if (btnAddV) {
                btnAddV.addEventListener('click', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    var count = parseInt(vToolbar.querySelector('#bulk-variant-count').value, 10) || 1;
                    bulkAddVariantRows(count);
                });
            }
        }
    }

    // -------------------------------------------------------------
    // Listen for color input changes to dynamically update dropdowns
    // -------------------------------------------------------------
    document.addEventListener('input', function(e) {
        if (e.target && e.target.name && e.target.name.indexOf('variant_items') !== -1 && e.target.name.indexOf('color') !== -1) {
            updateBulkAddColorSelect();
        }
    });

    // Initialize on DOM load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            attachToolbars();
            doSyncVariantOptions();
        });
    } else {
        attachToolbars();
        doSyncVariantOptions();
    }

    setTimeout(attachToolbars, 250);
    setTimeout(attachToolbars, 700);
    setTimeout(attachToolbars, 1500);
})();
