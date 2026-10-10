(function() {
    'use strict';

    // Global file cache to guarantee zero file loss across the entire lifecycle
    window._adminFileCache = window._adminFileCache || new Map();

    // -----------------------------------------------------------------
    // 1. Instant File Cache Tracker (Zero File Loss)
    // -----------------------------------------------------------------
    document.addEventListener('change', function(e) {
        if (e.target && e.target.type === 'file' && e.target.name) {
            if (e.target.files && e.target.files.length > 0) {
                window._adminFileCache.set(e.target.name, e.target.files[0]);
            } else {
                var cached = window._adminFileCache.get(e.target.name);
                if (cached) {
                    try {
                        var dt = new DataTransfer();
                        dt.items.add(cached);
                        e.target.files = dt.files;
                    } catch (err) {}
                }
            }
        }
    }, true);

    function restoreAllCachedFiles(form) {
        if (!form || !window._adminFileCache) return;
        window._adminFileCache.forEach(function(file, fieldName) {
            var inp = form.querySelector('input[type="file"][name="' + fieldName + '"]');
            if (inp && (!inp.files || inp.files.length === 0)) {
                try {
                    var dt = new DataTransfer();
                    dt.items.add(file);
                    inp.files = dt.files;
                } catch (err) {
                    console.warn('DataTransfer restore notice:', err);
                }
            }
        });
    }

    // -----------------------------------------------------------------
    // 2. Instant Button Blocking & Live Progress Controllers
    // -----------------------------------------------------------------
    var isSubmitting = false;
    var lastClickedButton = null;

    window.updateLiveProgress = function(percent, loadedBytes, totalBytes) {
        var pct = Math.max(0, Math.min(100, Math.round(percent)));
        
        var radial = document.getElementById('admin-fullscreen-radial');
        var pctText = document.getElementById('admin-fullscreen-percent-text');
        var barInner = document.getElementById('admin-fullscreen-bar-inner');
        var byteText = document.getElementById('admin-fullscreen-bytes');
        var subTitle = document.getElementById('admin-fullscreen-subtitle');

        if (radial) radial.style.setProperty('--value', pct);
        if (pctText) pctText.textContent = pct + '%';
        if (barInner) barInner.style.width = pct + '%';

        if (loadedBytes && totalBytes && byteText && totalBytes > 0) {
            var mbLoaded = (loadedBytes / (1024 * 1024)).toFixed(1);
            var mbTotal = (totalBytes / (1024 * 1024)).toFixed(1);
            byteText.textContent = mbLoaded + ' MB / ' + mbTotal + ' MB';
            byteText.style.display = 'block';
        } else if (byteText && (!totalBytes || totalBytes <= 0)) {
            byteText.style.display = 'none';
        }

        if (pct >= 100 && subTitle) {
            subTitle.textContent = 'Saved successfully ✓';
        }
    };

    window.showFullscreenLoading = function(title, subtitle) {
        var fsLoader = document.getElementById('admin-fullscreen-loader');
        var fsTitle = document.getElementById('admin-fullscreen-title');
        var fsSub = document.getElementById('admin-fullscreen-subtitle');
        if (fsTitle && title) fsTitle.textContent = title;
        if (fsSub && subtitle) fsSub.textContent = subtitle;
        
        window.updateLiveProgress(5, 0, 0);

        if (fsLoader) {
            fsLoader.style.display = 'flex';
        }

        var progressBar = document.getElementById('admin-progress-bar');
        if (progressBar) {
            progressBar.style.display = 'block';
        }
    };

    window.resetSubmitState = function(form) {
        isSubmitting = false;
        if (form) delete form.dataset.isSubmitting;

        var fsLoader = document.getElementById('admin-fullscreen-loader');
        if (fsLoader) fsLoader.style.display = 'none';

        var progressBar = document.getElementById('admin-progress-bar');
        if (progressBar) progressBar.style.display = 'none';

        window.updateLiveProgress(0, 0, 0);

        document.querySelectorAll('.admin-btn-loading, .admin-btn-disabled-sibling').forEach(function(el) {
            el.classList.remove('admin-btn-loading', 'admin-btn-disabled-sibling');
            el.style.pointerEvents = '';
            var sp = el.querySelector('.admin-btn-spinner');
            if (sp) sp.remove();
            var ic = el.querySelector('i');
            if (ic) ic.style.display = '';
        });
    };

    window.showGlobalLoading = function(actionTitle, subTitle, activeBtn) {
        // 1. Show Fullscreen Overlay with Live Percentage
        window.showFullscreenLoading(actionTitle, subTitle);

        // 2. Instant Button Spinner on Active Button
        if (activeBtn) {
            activeBtn.classList.add('admin-btn-loading');
            activeBtn.style.pointerEvents = 'none';

            if (activeBtn.tagName && activeBtn.tagName.toLowerCase() === 'input') {
                activeBtn.dataset.originalVal = activeBtn.value;
                activeBtn.value = actionTitle;
            } else {
                var iconOnly = activeBtn.querySelector('i');
                if (iconOnly) iconOnly.style.display = 'none';

                if (!activeBtn.querySelector('.admin-btn-spinner')) {
                    var spinner = document.createElement('span');
                    spinner.className = 'admin-btn-spinner';
                    activeBtn.prepend(spinner);
                }
            }
        }

        // 3. Next millisecond block all other buttons across the page
        var allActionButtons = document.querySelectorAll('input[type="submit"], button[type="submit"], .submit-row button, .submit-row input, .submit-row a.button, .submit-row a.closelink, .submit-row a.deletelink, button.btn-primary, button.btn-error');
        allActionButtons.forEach(function(b) {
            if (b !== activeBtn) {
                b.classList.add('admin-btn-disabled-sibling');
                b.style.pointerEvents = 'none';
            }
        });
    };

    // -----------------------------------------------------------------
    // 3. Track Clicked Button & Deletion Navigations
    // -----------------------------------------------------------------
    document.addEventListener('pointerdown', function(e) {
        var btn = e.target.closest('input[type="submit"], button[type="submit"], .submit-row button, .submit-row input');
        if (btn) {
            lastClickedButton = {
                name: btn.getAttribute('name') || '_save',
                value: (btn.getAttribute('value') || btn.textContent || 'Save').trim(),
                element: btn
            };
        }
    }, true);

    document.addEventListener('click', function(e) {
        var btn = e.target.closest('input[type="submit"], button[type="submit"], .submit-row button, .submit-row input, a.deletelink');
        if (btn) {
            if (btn.tagName === 'A' && btn.classList.contains('deletelink')) {
                window.showGlobalLoading('Deleting item...', 'Navigating to confirmation screen', btn);
                return;
            }
            lastClickedButton = {
                name: btn.getAttribute('name') || '_save',
                value: (btn.getAttribute('value') || btn.textContent || 'Save').trim(),
                element: btn
            };
        }
    }, true);

    document.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            var form = e.target.closest('form');
            if (form && !isSubmitting && window._batchModeActive !== true) {
                var defaultBtn = form.querySelector('button[type="submit"][name="_save"], input[type="submit"][name="_save"], button[type="submit"].default, input[type="submit"].default, button[type="submit"], input[type="submit"]');
                if (defaultBtn) {
                    lastClickedButton = {
                        name: defaultBtn.getAttribute('name') || '_save',
                        value: (defaultBtn.getAttribute('value') || defaultBtn.textContent || 'Save').trim(),
                        element: defaultBtn
                    };
                }
            }
        }
    }, true);

    // -----------------------------------------------------------------
    // 4. Live ID Availability Pre-Checker
    // -----------------------------------------------------------------
    function initIdChecker(form) {
        var idInput = form.querySelector('#id_id, input[name="id"]');
        if (!idInput) return;

        var pathname = window.location.pathname;
        var isCategory = pathname.indexOf('/category/') !== -1 || (form.id && form.id.indexOf('category') !== -1);
        var isProduct = pathname.indexOf('/product/') !== -1 || (form.id && form.id.indexOf('product') !== -1);
        var modelType = isCategory ? 'category' : (isProduct ? 'product' : '');

        var pathParts = pathname.split('/').filter(Boolean);
        var currentPk = '';
        var changeIdx = pathParts.indexOf('change');
        if (changeIdx > 0) currentPk = pathParts[changeIdx - 1];

        if (modelType) {
            var debounceTimer = null;
            var feedbackContainer = form.querySelector('.id-availability-feedback');
            if (!feedbackContainer) {
                feedbackContainer = document.createElement('div');
                feedbackContainer.className = 'id-availability-feedback';
                feedbackContainer.style.marginTop = '6px';
                idInput.parentNode.appendChild(feedbackContainer);
            }

            function checkIdAvailability() {
                var val = (idInput.value || '').trim();
                if (!val) {
                    form.dataset.idDuplicate = 'false';
                    feedbackContainer.innerHTML = '<span style="color: #94a3b8; font-size: 11px;">ℹ️ Leave blank to auto-generate a unique ID.</span>';
                    idInput.style.borderColor = '';
                    return;
                }

                var url = '/api/check-id/?type=' + encodeURIComponent(modelType) + '&id=' + encodeURIComponent(val);
                if (currentPk) url += '&exclude_pk=' + encodeURIComponent(currentPk);

                fetch(url)
                    .then(function(res) { return res.json(); })
                    .then(function(data) {
                        if (data.available === false) {
                            form.dataset.idDuplicate = 'true';
                            feedbackContainer.innerHTML = '<span style="color: #ef4444; font-weight: 600; font-size: 12px; display: flex; align-items: center; gap: 4px;">⚠️ ' + (data.message || 'ID is already in use') + '. Please choose another ID or leave blank.</span>';
                            idInput.style.borderColor = '#ef4444';
                            idInput.style.boxShadow = '0 0 0 1px #ef4444';
                        } else {
                            form.dataset.idDuplicate = 'false';
                            feedbackContainer.innerHTML = '<span style="color: #10b981; font-weight: 600; font-size: 12px; display: flex; align-items: center; gap: 4px;">✓ ID is available.</span>';
                            idInput.style.borderColor = '#10b981';
                            idInput.style.boxShadow = '0 0 0 1px #10b981';
                        }
                    })
                    .catch(function() {
                        form.dataset.idDuplicate = 'false';
                        feedbackContainer.innerHTML = '';
                        idInput.style.borderColor = '';
                        idInput.style.boxShadow = '';
                    });
            }

            idInput.addEventListener('input', function() {
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(checkIdAvailability, 250);
            });
            idInput.addEventListener('blur', checkIdAvailability);
            if (idInput.value) checkIdAvailability();
        }
    }

    // -----------------------------------------------------------------
    // 5. AJAX Form Submitter with Live Real-time Percentage (XHR)
    // -----------------------------------------------------------------
    document.addEventListener('submit', function(e) {
        var form = e.target;
        if (!form || !(form instanceof HTMLFormElement)) return;

        // If batch mode is active, skip single submit
        if (window._batchModeActive === true) {
            return;
        }

        // Only intercept admin change forms
        var isChangeForm = (form.enctype && form.enctype.indexOf('multipart') !== -1) ||
                           (form.id && form.id.indexOf('_form') !== -1) ||
                           form.id === 'product_form' ||
                           form.id === 'category_form' ||
                           form.classList.contains('change-form');

        if (!isChangeForm) return;

        // Check for duplicate ID error
        var idInput = form.querySelector('#id_id, input[name="id"]');
        if (form.dataset.idDuplicate === 'true' && idInput && (idInput.value || '').trim()) {
            e.preventDefault();
            e.stopImmediatePropagation();
            window.resetSubmitState(form);

            idInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
            idInput.focus();
            idInput.style.borderColor = '#ef4444';
            idInput.style.boxShadow = '0 0 0 3px rgba(239, 68, 68, 0.4)';

            alert('⚠️ Cannot save: ID "' + idInput.value.trim() + '" already exists.\n\nPlease choose a different ID or leave blank.');
            return false;
        }

        // Prevent duplicate submits
        if (form.dataset.isSubmitting === 'true' || isSubmitting) {
            e.preventDefault();
            return false;
        }

        isSubmitting = true;
        form.dataset.isSubmitting = 'true';

        // Intercept standard browser submit
        e.preventDefault();
        e.stopImmediatePropagation();

        var actionLabel = 'Saving changes & uploading media...';
        var subLabel = 'Uploading media to server...';
        var activeBtnEl = lastClickedButton ? lastClickedButton.element : null;

        if (lastClickedButton && lastClickedButton.name) {
            var bName = lastClickedButton.name;
            if (bName === '_continue') actionLabel = 'Saving & Continuing...';
            else if (bName === '_addanother') actionLabel = 'Saving & Adding Another...';
            else if (bName === '_saveasnew') actionLabel = 'Saving as New...';
        }

        window.showGlobalLoading(actionLabel, subLabel, activeBtnEl);

        // Restore cached files into inputs
        restoreAllCachedFiles(form);

        // Check if any file inputs actually have files selected
        var hasFiles = false;
        var totalFileBytes = 0;
        form.querySelectorAll('input[type="file"]').forEach(function(fi) {
            if (fi.files && fi.files.length > 0) {
                for (var f = 0; f < fi.files.length; f++) {
                    if (fi.files[f].size > 0) {
                        hasFiles = true;
                        totalFileBytes += fi.files[f].size;
                    }
                }
            }
        });

        var currentPct = hasFiles ? 8 : 18;
        window.updateLiveProgress(currentPct, 0, totalFileBytes);

        var subTitle = document.getElementById('admin-fullscreen-subtitle');
        if (subTitle) {
            subTitle.textContent = hasFiles ? 'Uploading media to server...' : 'Saving changes & updating database...';
        }

        var formData = new FormData(form);
        if (lastClickedButton && lastClickedButton.name) {
            formData.set(lastClickedButton.name, lastClickedButton.value || '1');
        } else {
            formData.set('_save', 'Save');
        }

        var postUrl = form.action || window.location.href;

        // Use XMLHttpRequest for real-time percentage progress
        var xhr = new XMLHttpRequest();
        xhr.open('POST', postUrl, true);
        xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
        xhr.timeout = 180000; // 3 min safety timeout

        var singleProgressTimer = null;

        function startServerProcessingTicker() {
            if (singleProgressTimer) return;
            singleProgressTimer = setInterval(function() {
                if (currentPct < 99) {
                    var step = currentPct < 60 ? 3.5 : (currentPct < 85 ? 1.8 : (currentPct < 94 ? 0.7 : (currentPct < 98 ? 0.2 : 0.05)));
                    currentPct = Math.min(99, currentPct + step);
                    var displayPct = Math.floor(currentPct);
                    if (subTitle) {
                        var msg = displayPct < 60 ? 'Processing form data' : (displayPct < 85 ? 'Updating database records' : (displayPct < 95 ? 'Syncing cloud storage' : 'Finalizing transaction'));
                        subTitle.textContent = msg + ' (' + displayPct + '%)';
                    }
                    window.updateLiveProgress(displayPct, totalFileBytes, totalFileBytes);
                }
            }, 100);
        }

        // If no files attached, immediately start progress ticker so there is ZERO delay at 0%
        if (!hasFiles) {
            startServerProcessingTicker();
        }

        // Phase 1: Upload stream (8% -> 60%)
        xhr.upload.onprogress = function(event) {
            if (event.lengthComputable && event.total > 0 && hasFiles) {
                var rawPercent = (event.loaded / event.total);
                var scaledPercent = Math.max(8, Math.round(rawPercent * 60));
                currentPct = scaledPercent;
                window.updateLiveProgress(scaledPercent, event.loaded, event.total);
            }
        };

        // Phase 2: Upload done -> Server & Cloud storage processing
        xhr.upload.onload = function() {
            currentPct = Math.max(currentPct, 60);
            startServerProcessingTicker();
        };

        // Safety fallback: If upload listener hasn't fired in 250ms, start ticker anyway
        setTimeout(function() {
            if (!singleProgressTimer && isSubmitting) {
                startServerProcessingTicker();
            }
        }, 250);

        xhr.onload = function() {
            clearInterval(singleProgressTimer);

            var responseHtml = xhr.responseText || '';
            var parser = new DOMParser();
            var doc = parser.parseFromString(responseHtml, 'text/html');

            var newErrorNote = doc.querySelector('.errornote, .alert-error, div.errors, ul.errorlist, .id-injected-error');

            // If no errors and status 200 / 302, it is a success!
            if (!newErrorNote && (xhr.status === 200 || xhr.status === 302)) {
                window.updateLiveProgress(100);
                if (xhr.responseURL && xhr.responseURL !== window.location.href) {
                    window.location.href = xhr.responseURL;
                } else {
                    window.location.reload();
                }
                return;
            }

            // Validation Error (Django 200 OK) -> Unblock buttons & map errors in-place
            window.resetSubmitState(form);

            // Clean old errors
            form.querySelectorAll('.errornote, .alert-error, div.errors, .id-injected-error').forEach(function(el) { el.remove(); });
            form.querySelectorAll('.errorlist, .text-error').forEach(function(el) { el.remove(); });

            // Insert top error note
            if (newErrorNote) {
                var importedNote = document.importNode(newErrorNote, true);
                importedNote.classList.add('id-injected-error');
                form.insertBefore(importedNote, form.firstChild);
            }

            // Map field errors into current DOM
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
                            if (!firstErrorInp) {
                                firstErrorInp = currentInp;
                            }
                        }
                    }
                }
            });

            // Sync tab badges and indicators from parsed response
            var newTabs = doc.querySelectorAll('.tabs a, .tabs button, [role="tab"], .tab');
            var currentTabs = document.querySelectorAll('.tabs a, .tabs button, [role="tab"], .tab');
            if (newTabs.length && currentTabs.length) {
                newTabs.forEach(function(nTab, idx) {
                    if (currentTabs[idx]) {
                        var errBadge = nTab.querySelector('.badge-error, .badge, [class*="badge"]');
                        var curBadge = currentTabs[idx].querySelector('.badge-error, .badge, [class*="badge"]');
                        if (errBadge && curBadge) {
                            curBadge.innerHTML = errBadge.innerHTML;
                            curBadge.className = errBadge.className;
                            curBadge.style.display = '';
                        } else if (errBadge && !curBadge) {
                            currentTabs[idx].appendChild(document.importNode(errBadge, true));
                        } else if (!errBadge && curBadge) {
                            curBadge.remove();
                        }
                    }
                });
            }

            // Auto-switch to tab containing error
            if (firstErrorInp) {
                var parentTabPanel = firstErrorInp.closest('.tab-content, [role="tabpanel"], fieldset, div[id*="tab"]');
                if (parentTabPanel) {
                    var panelId = parentTabPanel.id;
                    var tabBtn = document.querySelector('[data-tab-target="#' + CSS.escape(panelId) + '"], a[href="#' + CSS.escape(panelId) + '"], button[data-tab="' + CSS.escape(panelId) + '"]');
                    if (tabBtn) tabBtn.click();
                }

                var firstErrorTab = document.querySelector('.tabs .badge-error, .tabs [class*="error"], [role="tab"] .badge-error');
                if (firstErrorTab) {
                    var clickableTab = firstErrorTab.closest('a, button, .tab');
                    if (clickableTab) clickableTab.click();
                }

                firstErrorInp.scrollIntoView({ behavior: 'smooth', block: 'center' });
                try { firstErrorInp.focus(); } catch (e) {}
            } else {
                var firstErr = form.querySelector('.id-injected-error, .alert-error, .errornote, .errorlist');
                if (firstErr) firstErr.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }

            // Restore all file inputs from cache
            restoreAllCachedFiles(form);
        };

        xhr.ontimeout = function() {
            clearInterval(singleProgressTimer);
            window.resetSubmitState(form);
            restoreAllCachedFiles(form);
            alert('⚠️ Upload timed out. Please check your internet connection and try again.');
        };

        xhr.onerror = function() {
            clearInterval(singleProgressTimer);
            window.resetSubmitState(form);
            restoreAllCachedFiles(form);
            alert('⚠️ Network error occurred while saving. Your inputs and files have been preserved.');
        };

        xhr.send(formData);
        return false;
    }, true);

    // Init ID checker on load
    function initAll() {
        var forms = document.querySelectorAll('#product_form, #category_form, form[id$="_form"], form.change-form');
        forms.forEach(function(f) {
            initIdChecker(f);
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initAll);
    } else {
        initAll();
    }
    setTimeout(initAll, 300);

    // Reset when navigating back via Back/Forward cache (bfcache)
    window.addEventListener('pageshow', function(event) {
        if (event.persisted) {
            window.resetSubmitState(null);
        }
    });
})();
