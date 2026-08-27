/* ---------------------------------------------------------------------------
   api.js
   Single place where the mock frontend addresses the FastAPI backend.

   Override at runtime without editing this file:
     ?api=http://localhost:8090        (query string, remembered in sessionStorage)
   --------------------------------------------------------------------------- */

(function (root) {
  'use strict';

  var DEFAULT_BASE = 'https://apex-workflow-backend-production.up.railway.app';

  /* Hostnames that can only be the developer's own machine, a container's view
     of it, or a private network -- never the public deployment. */
  function isLocalOrigin() {
    var host = location.hostname;
    return host === 'localhost' || host === '127.0.0.1' || host === '0.0.0.0' ||
           host === '::1' || host === '[::1]' ||
           /(^|\.)localhost$/.test(host) ||
           /\.internal$/.test(host) ||          /* host.docker.internal */
           /\.local$/.test(host) ||
           /^192\.168\./.test(host) ||
           /^10\./.test(host) ||
           /^172\.(1[6-9]|2[0-9]|3[01])\./.test(host);
  }

  function resolveBase() {
    try {
      var q = new URLSearchParams(location.search).get('api');
      if (q) {
        sessionStorage.setItem('apex_api_base', q.replace(/\/+$/, ''));
        return q.replace(/\/+$/, '');
      }
      var saved = sessionStorage.getItem('apex_api_base');
      if (saved) return saved;
    } catch (e) { /* sandboxed iframe without storage */ }

    // Served by the mock backend itself? Then talk to the same origin.
    //
    // This tested `location.port === '8090'` alone, which failed two ways the
    // moment the mock moved off that port: the same copy then addressed the
    // SHARED HOSTED backend, so a local test wrote to real data, and a local
    // backend that WAS running looked like an offline outage because nothing
    // ever called it. Decide on the host instead, keeping the port as a
    // fallback so an existing 8090 setup behaves exactly as before.
    if (location.protocol === 'http:' || location.protocol === 'https:') {
      if (isLocalOrigin() || location.port === '8090') return location.origin;
    }
    return DEFAULT_BASE;
  }

  var BASE = resolveBase();

  function url(path) { return BASE + path; }

  async function getJSON(path) {
    var res = await fetch(url(path));
    if (!res.ok) throw new Error('HTTP ' + res.status);
    return res.json();
  }

  async function postForm(path, formData) {
    var res = await fetch(url(path), { method: 'POST', body: formData });
    var data = await res.json().catch(function () { return {}; });
    if (!res.ok) throw new Error(data.detail || ('HTTP ' + res.status));
    return data;
  }

  async function postJSON(path, body) {
    var res = await fetch(url(path), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    var data = await res.json().catch(function () { return {}; });
    if (!res.ok) throw new Error(data.detail || ('HTTP ' + res.status));
    return data;
  }

  async function patchJSON(path, body) {
    var res = await fetch(url(path), {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    var data = await res.json().catch(function () { return {}; });
    if (!res.ok) throw new Error(data.detail || ('HTTP ' + res.status));
    return data;
  }

  /* Map an /api/import-confirm row onto the grid's field names. */
  function rowFromApi(r) {
    return {
      status:       r.status || 'New',
      abiStatus:    r.abi_query_status || 'New',
      abiMatch:     r.abi_query_match || 'Not Existing',
      tags:         r.tags || '',
      uld:          r.uld_no || '',
      customer:     r.hawb_customer || '',
      mno:          r.mawb || '',
      hno:          r.hawb || '',
      eta:          r.eta || '',
      pol:          r.pol || '',
      pod:          r.pod || '',
      airline:      r.airline || '',
      firm:         r.firm_code || '',
      flight:       r.flight_no || '',
      destHandling: r.dest_handling_office || '',
      destGateway:  r.dest_gateway_office || '',
      addr:         r.address || '',
      lfd:          r.last_free_date || '',
      wt:           r.wt || '',
      scStatus:     r.sc_job_status || '',
      opRem:        r.op_remarks || '',
      scJob:        r.sc_job_no || '',
      preAlert:     r.pre_alert_date || '',
      destCs:       r.dest_cs || '',
      isOvs:        r.is_ovs_agent || '',
      qSend:        r.query_send_date || '',
      qUpdate:      r.query_update_date || '',
      operator:     r.operator || ''
    };
  }

  root.APEX_API = {
    base: BASE,
    url: url,
    getJSON: getJSON,
    postForm: postForm,
    postJSON: postJSON,
    patchJSON: patchJSON,
    rowFromApi: rowFromApi
  };
})(typeof window !== 'undefined' ? window : this);
