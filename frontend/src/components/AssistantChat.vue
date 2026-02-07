<template>
  <div
    class="flex flex-col h-full bg-white/95 dark:bg-slate-900/95 backdrop-blur-sm border-l border-slate-200/80 dark:border-slate-800/80 overflow-hidden relative"
  >
    <!-- Default provider notification -->
    <transition
      enter-active-class="transition ease-out duration-200"
      enter-from-class="opacity-0 translate-y-2"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition ease-in duration-150"
      leave-from-class="opacity-100 translate-y-0"
      leave-to-class="opacity-0 translate-y-2"
    >
      <div
        v-if="defaultProviderNotification"
        class="absolute top-4 left-1/2 transform -translate-x-1/2 z-50 px-4 py-2 bg-amber-500 text-white text-sm font-medium rounded-lg shadow-lg flex items-center gap-2"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="h-4 w-4"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="2"
        >
          <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
        </svg>
        {{ defaultProviderNotification }}
      </div>
    </transition>

    <!-- Header -->
    <div class="flex flex-col border-b border-slate-200 dark:border-slate-800/80">
      <!-- Title row -->
      <div class="flex items-center justify-between px-4 py-3 bg-slate-50 dark:bg-slate-950/50">
        <div class="flex items-center gap-2">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-5 w-5 text-violet-500 dark:text-violet-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456z"
            />
          </svg>
          <h2 class="font-semibold text-slate-800 dark:text-slate-100">Network Assistant</h2>
        </div>
        <!-- Close button -->
        <button
          @click="$emit('close')"
          class="p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-400 transition-colors"
          title="Close assistant"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-5 w-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2"
          >
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
      <!-- Model selection row (hidden in cloud deployment) -->
      <div
        v-if="!isCloudDeployment"
        class="flex items-center gap-2 px-4 py-2 bg-slate-100/50 dark:bg-slate-900/50 border-t border-slate-200/50 dark:border-slate-800/50"
      >
        <!-- Provider icon buttons -->
        <div class="flex items-center gap-1">
          <button
            v-for="p in allProviders"
            :key="p.provider"
            @click="p.available && !rateLimited ? selectProvider(p.provider) : null"
            @dblclick="p.available && !rateLimited ? setDefaultProvider(p.provider) : null"
            :disabled="inputDisabled || !p.available"
            class="p-1.5 rounded-md transition-all relative"
            :class="[
              selectedProvider === p.provider
                ? 'bg-slate-200 dark:bg-slate-800 ring-2 ring-violet-500'
                : p.available && !rateLimited
                  ? 'hover:bg-slate-200 dark:hover:bg-slate-800'
                  : '',
              inputDisabled || !p.available ? 'opacity-30 cursor-not-allowed' : '',
            ]"
            :title="rateLimited ? 'Rate limited - try again tomorrow' : getProviderTitle(p)"
          >
            <!-- Default provider indicator -->
            <span
              v-if="p.provider === userDefaultProvider && p.available"
              class="absolute -top-0.5 -right-0.5 w-2 h-2 bg-amber-400 dark:bg-amber-500 rounded-full border border-white dark:border-slate-900"
              title="Your default provider"
            ></span>
            <!-- OpenAI icon (monochrome/black) -->
            <svg
              v-if="p.provider === 'openai'"
              class="h-5 w-5"
              :class="
                selectedProvider === p.provider
                  ? 'text-slate-900 dark:text-white'
                  : 'text-slate-400 dark:text-slate-500'
              "
              viewBox="0 0 24 24"
              fill="currentColor"
            >
              <path
                d="M22.2819 9.8211a5.9847 5.9847 0 0 0-.5157-4.9108 6.0462 6.0462 0 0 0-6.5098-2.9A6.0651 6.0651 0 0 0 4.9807 4.1818a5.9847 5.9847 0 0 0-3.9977 2.9 6.0462 6.0462 0 0 0 .7427 7.0966 5.98 5.98 0 0 0 .511 4.9107 6.051 6.051 0 0 0 6.5146 2.9001A5.9847 5.9847 0 0 0 13.2599 24a6.0557 6.0557 0 0 0 5.7718-4.2058 5.9894 5.9894 0 0 0 3.9977-2.9001 6.0557 6.0557 0 0 0-.7475-7.0729zm-9.022 12.6081a4.4755 4.4755 0 0 1-2.8764-1.0408l.1419-.0804 4.7783-2.7582a.7948.7948 0 0 0 .3927-.6813v-6.7369l2.02 1.1686a.071.071 0 0 1 .038.052v5.5826a4.504 4.504 0 0 1-4.4945 4.4944zm-9.6607-4.1254a4.4708 4.4708 0 0 1-.5346-3.0137l.142.0852 4.783 2.7582a.7712.7712 0 0 0 .7806 0l5.8428-3.3685v2.3324a.0804.0804 0 0 1-.0332.0615L9.74 19.9502a4.4992 4.4992 0 0 1-6.1408-1.6464zM2.3408 7.8956a4.485 4.485 0 0 1 2.3655-1.9728V11.6a.7664.7664 0 0 0 .3879.6765l5.8144 3.3543-2.0201 1.1685a.0757.0757 0 0 1-.071 0l-4.8303-2.7865A4.504 4.504 0 0 1 2.3408 7.872zm16.5963 3.8558L13.1038 8.364 15.1192 7.2a.0757.0757 0 0 1 .071 0l4.8303 2.7913a4.4944 4.4944 0 0 1-.6765 8.1042v-5.6772a.79.79 0 0 0-.407-.667zm2.0107-3.0231l-.142-.0852-4.7735-2.7818a.7759.7759 0 0 0-.7854 0L9.409 9.2297V6.8974a.0662.0662 0 0 1 .0284-.0615l4.8303-2.7866a4.4992 4.4992 0 0 1 6.6802 4.66zM8.3065 12.863l-2.02-1.1638a.0804.0804 0 0 1-.038-.0567V6.0742a4.4992 4.4992 0 0 1 7.3757-3.4537l-.142.0805L8.704 5.459a.7948.7948 0 0 0-.3927.6813zm1.0976-2.3654l2.602-1.4998 2.6069 1.4998v2.9994l-2.5974 1.4997-2.6067-1.4997Z"
              />
            </svg>
            <!-- Anthropic/Claude icon (terracotta colored) -->
            <svg
              v-else-if="p.provider === 'anthropic'"
              class="h-5 w-5"
              viewBox="0 0 1200 1200"
              :fill="selectedProvider === p.provider ? '#d97757' : '#94a3b8'"
            >
              <path
                d="M 233.959793 800.214905 L 468.644287 668.536987 L 472.590637 657.100647 L 468.644287 650.738403 L 457.208069 650.738403 L 417.986633 648.322144 L 283.892639 644.69812 L 167.597321 639.865845 L 54.926208 633.825623 L 26.577238 627.785339 L 3.3e-05 592.751709 L 2.73832 575.27533 L 26.577238 559.248352 L 60.724873 562.228149 L 136.187973 567.382629 L 249.422867 575.194763 L 331.570496 580.026978 L 453.261841 592.671082 L 472.590637 592.671082 L 475.328857 584.859009 L 468.724915 580.026978 L 463.570557 575.194763 L 346.389313 495.785217 L 219.543671 411.865906 L 153.100723 363.543762 L 117.181267 339.060425 L 99.060455 316.107361 L 91.248367 266.01355 L 123.865784 230.093994 L 167.677887 233.073853 L 178.872513 236.053772 L 223.248367 270.201477 L 318.040283 343.570496 L 441.825592 434.738342 L 459.946411 449.798706 L 467.194672 444.64447 L 468.080597 441.020203 L 459.946411 427.409485 L 392.617493 305.718323 L 320.778564 181.932983 L 288.80542 130.630859 L 280.348999 99.865845 C 277.369171 87.221436 275.194641 76.590698 275.194641 63.624268 L 312.322174 13.20813 L 332.8591 6.604126 L 382.389313 13.20813 L 403.248352 31.328979 L 434.013519 101.71814 L 483.865753 212.537048 L 561.181274 363.221497 L 583.812134 407.919434 L 595.892639 449.315491 L 600.40271 461.959839 L 608.214783 461.959839 L 608.214783 454.711609 L 614.577271 369.825623 L 626.335632 265.61084 L 637.771851 131.516846 L 641.718201 93.745117 L 660.402832 48.483276 L 697.530334 24.000122 L 726.52356 37.852417 L 750.362549 72 L 747.060486 94.067139 L 732.886047 186.201416 L 705.100708 330.52356 L 686.979919 427.167847 L 697.530334 427.167847 L 709.61084 415.087341 L 758.496704 350.174561 L 840.644348 247.490051 L 876.885925 206.738342 L 919.167847 161.71814 L 946.308838 140.29541 L 997.61084 140.29541 L 1035.38269 196.429626 L 1018.469849 254.416199 L 965.637634 321.422852 L 921.825562 378.201538 L 859.006714 462.765259 L 819.785278 530.41626 L 823.409424 535.812073 L 832.75177 534.92627 L 974.657776 504.724915 L 1051.328979 490.872559 L 1142.818848 475.167786 L 1184.214844 494.496582 L 1188.724854 514.147644 L 1172.456421 554.335693 L 1074.604126 578.496765 L 959.838989 601.449829 L 788.939636 641.879272 L 786.845764 643.409485 L 789.261841 646.389343 L 866.255127 653.637634 L 899.194702 655.409424 L 979.812134 655.409424 L 1129.932861 666.604187 L 1169.154419 692.537109 L 1192.671265 724.268677 L 1188.724854 748.429688 L 1128.322144 779.194641 L 1046.818848 759.865845 L 856.590759 714.604126 L 791.355774 698.335754 L 782.335693 698.335754 L 782.335693 703.731567 L 836.69812 756.885986 L 936.322205 846.845581 L 1061.073975 962.81897 L 1067.436279 991.490112 L 1051.409424 1014.120911 L 1034.496704 1011.704712 L 924.885986 929.234924 L 882.604126 892.107544 L 786.845764 811.48999 L 780.483276 811.48999 L 780.483276 819.946289 L 802.550415 852.241699 L 919.087341 1027.409424 L 925.127625 1081.127686 L 916.671204 1098.604126 L 886.469849 1109.154419 L 853.288696 1103.114136 L 785.073914 1007.355835 L 714.684631 899.516785 L 657.906067 802.872498 L 650.979858 806.81897 L 617.476624 1167.704834 L 601.771851 1186.147705 L 565.530212 1200 L 535.328857 1177.046997 L 519.302124 1139.919556 L 535.328857 1066.550537 L 554.657776 970.792053 L 570.362488 894.68457 L 584.536926 800.134277 L 592.993347 768.724976 L 592.429626 766.630859 L 585.503479 767.516968 L 514.22821 865.369263 L 405.825531 1011.865906 L 320.053711 1103.677979 L 299.516815 1111.812256 L 263.919525 1093.369263 L 267.221497 1060.429688 L 287.114136 1031.114136 L 405.825531 880.107361 L 477.422913 786.52356 L 523.651062 732.483276 L 523.328918 724.671265 L 520.590698 724.671265 L 205.288605 929.395935 L 149.154434 936.644409 L 124.993355 914.01355 L 127.973183 876.885986 L 139.409409 864.80542 L 234.201385 799.570435 L 233.879227 799.8927 Z"
              />
            </svg>
            <!-- Gemini icon (gradient colored) -->
            <svg
              v-else-if="p.provider === 'gemini'"
              class="h-5 w-5"
              viewBox="0 0 16 16"
              fill="none"
            >
              <path
                d="M16 8.016A8.522 8.522 0 008.016 16h-.032A8.521 8.521 0 000 8.016v-.032A8.521 8.521 0 007.984 0h.032A8.522 8.522 0 0016 7.984v.032z"
                :fill="selectedProvider === p.provider ? 'url(#gemini-gradient-active)' : '#94a3b8'"
              />
              <defs>
                <radialGradient
                  id="gemini-gradient-active"
                  cx="0"
                  cy="0"
                  r="1"
                  gradientUnits="userSpaceOnUse"
                  gradientTransform="matrix(16.1326 5.4553 -43.70045 129.2322 1.588 6.503)"
                >
                  <stop offset=".067" stop-color="#9168C0" />
                  <stop offset=".343" stop-color="#5684D1" />
                  <stop offset=".672" stop-color="#1BA1E3" />
                </radialGradient>
              </defs>
            </svg>
            <!-- Ollama icon (monochrome/black) -->
            <svg
              v-else-if="p.provider === 'ollama'"
              class="h-5 w-5"
              :class="
                selectedProvider === p.provider
                  ? 'text-slate-900 dark:text-white'
                  : 'text-slate-400 dark:text-slate-500'
              "
              viewBox="0 0 24 24"
              fill="currentColor"
            >
              <path
                d="M7.905 1.09c.216.085.411.225.588.41.295.306.544.744.734 1.263.191.522.315 1.1.362 1.68a5.054 5.054 0 012.049-.636l.051-.004c.87-.07 1.73.087 2.48.474.101.053.2.11.297.17.05-.569.172-1.134.36-1.644.19-.52.439-.957.733-1.264a1.67 1.67 0 01.589-.41c.257-.1.53-.118.796-.042.401.114.745.368 1.016.737.248.337.434.769.561 1.287.23.934.27 2.163.115 3.645l.053.04.026.019c.757.576 1.284 1.397 1.563 2.35.435 1.487.216 3.155-.534 4.088l-.018.021.002.003c.417.762.67 1.567.724 2.4l.002.03c.064 1.065-.2 2.137-.814 3.19l-.007.01.01.024c.472 1.157.62 2.322.438 3.486l-.006.039a.651.651 0 01-.747.536.648.648 0 01-.54-.742c.167-1.033.01-2.069-.48-3.123a.643.643 0 01.04-.617l.004-.006c.604-.924.854-1.83.8-2.72-.046-.779-.325-1.544-.8-2.273a.644.644 0 01.18-.886l.009-.006c.243-.159.467-.565.58-1.12a4.229 4.229 0 00-.095-1.974c-.205-.7-.58-1.284-1.105-1.683-.595-.454-1.383-.673-2.38-.61a.653.653 0 01-.632-.371c-.314-.665-.772-1.141-1.343-1.436a3.288 3.288 0 00-1.772-.332c-1.245.099-2.343.801-2.67 1.686a.652.652 0 01-.61.425c-1.067.002-1.893.252-2.497.703-.522.39-.878.935-1.066 1.588a4.07 4.07 0 00-.068 1.886c.112.558.331 1.02.582 1.269l.008.007c.212.207.257.53.109.785-.36.622-.629 1.549-.673 2.44-.05 1.018.186 1.902.719 2.536l.016.019a.643.643 0 01.095.69c-.576 1.236-.753 2.252-.562 3.052a.652.652 0 01-1.269.298c-.243-1.018-.078-2.184.473-3.498l.014-.035-.008-.012a4.339 4.339 0 01-.598-1.309l-.005-.019a5.764 5.764 0 01-.177-1.785c.044-.91.278-1.842.622-2.59l.012-.026-.002-.002c-.293-.418-.51-.953-.63-1.545l-.005-.024a5.352 5.352 0 01.093-2.49c.262-.915.777-1.701 1.536-2.269.06-.045.123-.09.186-.132-.159-1.493-.119-2.73.112-3.67.127-.518.314-.95.562-1.287.27-.368.614-.622 1.015-.737.266-.076.54-.059.797.042zm4.116 9.09c.936 0 1.8.313 2.446.855.63.527 1.005 1.235 1.005 1.94 0 .888-.406 1.58-1.133 2.022-.62.375-1.451.557-2.403.557-1.009 0-1.871-.259-2.493-.734-.617-.47-.963-1.13-.963-1.845 0-.707.398-1.417 1.056-1.946.668-.537 1.55-.849 2.485-.849zm0 .896a3.07 3.07 0 00-1.916.65c-.461.37-.722.835-.722 1.25 0 .428.21.829.61 1.134.455.347 1.124.548 1.943.548.799 0 1.473-.147 1.932-.426.463-.28.7-.686.7-1.257 0-.423-.246-.89-.683-1.256-.484-.405-1.14-.643-1.864-.643zm.662 1.21l.004.004c.12.151.095.37-.056.49l-.292.23v.446a.375.375 0 01-.376.373.375.375 0 01-.376-.373v-.46l-.271-.218a.347.347 0 01-.052-.49.353.353 0 01.494-.051l.215.172.22-.174a.353.353 0 01.49.051zm-5.04-1.919c.478 0 .867.39.867.871a.87.87 0 01-.868.871.87.87 0 01-.867-.87.87.87 0 01.867-.872zm8.706 0c.48 0 .868.39.868.871a.87.87 0 01-.868.871.87.87 0 01-.867-.87.87.87 0 01.867-.872zM7.44 2.3l-.003.002a.659.659 0 00-.285.238l-.005.006c-.138.189-.258.467-.348.832-.17.692-.216 1.631-.124 2.782.43-.128.899-.208 1.404-.237l.01-.001.019-.034c.046-.082.095-.161.148-.239.123-.771.022-1.692-.253-2.444-.134-.364-.297-.65-.453-.813a.628.628 0 00-.107-.09L7.44 2.3zm9.174.04l-.002.001a.628.628 0 00-.107.09c-.156.163-.32.45-.453.814-.29.794-.387 1.776-.23 2.572l.058.097.008.014h.03a5.184 5.184 0 011.466.212c.086-1.124.038-2.043-.128-2.722-.09-.365-.21-.643-.349-.832l-.004-.006a.659.659 0 00-.285-.239h-.004z"
              />
            </svg>
            <!-- Default/fallback icon -->
            <svg
              v-else
              class="h-5 w-5"
              :class="
                selectedProvider === p.provider
                  ? 'text-slate-900 dark:text-white'
                  : 'text-slate-400 dark:text-slate-500'
              "
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="2"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23.693L5 14.5m14.8.8l1.402 1.402c1.232 1.232.65 3.318-1.067 3.611l-.646.108a6.002 6.002 0 01-1.878-.004L5.21 20.621c-1.717-.293-2.299-2.379-1.067-3.61L5.545 15.61"
              />
            </svg>
          </button>
        </div>

        <div class="w-px h-5 bg-slate-300 dark:bg-slate-700"></div>

        <!-- Model selector -->
        <select
          v-model="selectedModel"
          class="text-xs bg-white dark:bg-slate-800/60 border border-slate-300 dark:border-slate-700 rounded-md px-2 py-1.5 text-slate-700 dark:text-slate-200 focus:border-violet-500 focus:ring-1 focus:ring-violet-500 outline-none flex-1 min-w-0 transition-shadow"
          :disabled="inputDisabled || !currentProviderModels.length"
          :title="rateLimited ? 'Rate limited - try again tomorrow' : selectedModel"
        >
          <option v-for="model in currentProviderModels" :key="model" :value="model">
            {{ formatModelName(model) }}
          </option>
        </select>
      </div>
    </div>

    <!-- Messages Area -->
    <div
      ref="messagesContainer"
      class="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-50/50 dark:bg-slate-950/50"
    >
      <!-- Welcome message -->
      <div v-if="messages.length === 0" class="text-center py-8">
        <div
          class="inline-flex items-center justify-center w-14 h-14 rounded-xl bg-gradient-to-br from-violet-500 to-fuchsia-500 shadow-lg shadow-violet-500/20 mb-4"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-7 w-7 text-white"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="1.5"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456z"
            />
          </svg>
        </div>
        <h3 class="text-base font-semibold text-slate-800 dark:text-slate-100 mb-2">
          Hi! I'm your Network Assistant
        </h3>
        <p class="text-slate-500 dark:text-slate-400 text-sm max-w-md mx-auto mb-5">
          I can help you understand your network topology, troubleshoot issues, and answer questions
          about device health and connectivity.
        </p>
        <div class="flex flex-wrap justify-center gap-2">
          <button
            v-for="suggestion in suggestions"
            :key="suggestion"
            @click="sendMessage(suggestion)"
            class="px-3 py-1.5 text-xs bg-white dark:bg-slate-800/60 hover:bg-violet-50 dark:hover:bg-violet-900/30 border border-slate-200/80 dark:border-slate-700/50 hover:border-violet-400 dark:hover:border-violet-500 rounded-full text-slate-600 dark:text-slate-300 hover:text-violet-700 dark:hover:text-violet-300 transition-colors"
          >
            {{ suggestion }}
          </button>
        </div>
      </div>

      <!-- Message list -->
      <template v-for="(msg, idx) in messages" :key="idx">
        <!-- User message -->
        <div v-if="msg.role === 'user'" class="flex justify-end">
          <div
            class="max-w-[80%] bg-gradient-to-r from-violet-600 to-fuchsia-600 rounded-2xl rounded-tr-sm px-4 py-2.5 text-white text-sm shadow-sm"
          >
            <div
              class="prose prose-sm prose-invert prose-user max-w-none"
              v-html="formatMessage(msg.content)"
            ></div>
          </div>
        </div>

        <!-- Assistant message -->
        <div v-else class="flex gap-3">
          <div
            class="flex-shrink-0 w-7 h-7 rounded-lg bg-gradient-to-br from-violet-500 to-fuchsia-500 flex items-center justify-center shadow-sm shadow-violet-500/20"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-3.5 w-3.5 text-white"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="2"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z"
              />
            </svg>
          </div>
          <div
            class="max-w-[85%] bg-white dark:bg-slate-800/60 border border-slate-200/80 dark:border-slate-700/50 rounded-2xl rounded-tl-sm px-4 py-2.5 text-slate-700 dark:text-slate-200 text-sm shadow-sm"
          >
            <div
              class="prose prose-sm dark:prose-invert max-w-none"
              v-html="formatMessage(msg.content)"
            ></div>
          </div>
        </div>
      </template>

      <!-- Streaming indicator -->
      <div v-if="isStreaming && !currentStreamContent" class="flex gap-3">
        <div
          class="flex-shrink-0 w-7 h-7 rounded-lg bg-gradient-to-br from-violet-500 to-fuchsia-500 flex items-center justify-center shadow-sm shadow-violet-500/20"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-3.5 w-3.5 text-white animate-pulse"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z"
            />
          </svg>
        </div>
        <div
          class="bg-white dark:bg-slate-800/60 border border-slate-200/80 dark:border-slate-700/50 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm"
        >
          <div class="flex gap-1">
            <span
              class="w-2 h-2 bg-violet-500 rounded-full animate-bounce"
              style="animation-delay: 0ms"
            ></span>
            <span
              class="w-2 h-2 bg-violet-500 rounded-full animate-bounce"
              style="animation-delay: 150ms"
            ></span>
            <span
              class="w-2 h-2 bg-violet-500 rounded-full animate-bounce"
              style="animation-delay: 300ms"
            ></span>
          </div>
        </div>
      </div>

      <!-- Streaming content -->
      <div v-if="isStreaming && currentStreamContent" class="flex gap-3">
        <div
          class="flex-shrink-0 w-7 h-7 rounded-lg bg-gradient-to-br from-violet-500 to-fuchsia-500 flex items-center justify-center shadow-sm shadow-violet-500/20"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-3.5 w-3.5 text-white"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z"
            />
          </svg>
        </div>
        <div
          class="max-w-[85%] bg-white dark:bg-slate-800/60 border border-slate-200/80 dark:border-slate-700/50 rounded-2xl rounded-tl-sm px-4 py-2.5 text-slate-700 dark:text-slate-200 text-sm shadow-sm"
        >
          <div
            class="prose prose-sm dark:prose-invert max-w-none"
            v-html="formatMessage(currentStreamContent)"
          ></div>
          <span class="inline-block w-2 h-4 bg-violet-500 animate-pulse ml-0.5"></span>
        </div>
      </div>

      <!-- Error message -->
      <div v-if="error" class="flex gap-3">
        <div
          class="flex-shrink-0 w-7 h-7 rounded-lg bg-red-100 dark:bg-red-900/30 flex items-center justify-center"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-3.5 w-3.5 text-red-500 dark:text-red-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
        </div>
        <div
          class="max-w-[85%] bg-red-50 dark:bg-red-900/20 border border-red-200/80 dark:border-red-800/50 rounded-2xl rounded-tl-sm px-4 py-2.5 text-red-700 dark:text-red-300 text-sm"
        >
          {{ error }}
        </div>
      </div>
    </div>

    <!-- Context indicator -->
    <div
      class="px-4 py-2 bg-slate-100/80 dark:bg-slate-900/60 border-t border-slate-200/80 dark:border-slate-800/80 flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400"
    >
      <!-- Loading state -->
      <template v-if="contextLoading">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="h-4 w-4 text-amber-500 animate-spin"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="2"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
          />
        </svg>
        <span class="text-amber-600 dark:text-amber-400">Loading network context...</span>
      </template>
      <!-- Ready state -->
      <template v-else-if="contextSummary && contextSummary.total_nodes > 0">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="h-4 w-4 text-emerald-500"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="2"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        <span
          >Network context: {{ contextSummary.total_nodes }} devices ({{
            contextSummary.healthy_nodes
          }}
          healthy)</span
        >
      </template>
      <!-- Unavailable state -->
      <template v-else>
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="h-4 w-4 text-slate-400 dark:text-slate-500"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="2"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"
          />
        </svg>
        <span class="text-slate-400 dark:text-slate-500">Network context unavailable</span>
      </template>
      <!-- Refresh button -->
      <button
        @click="refreshContext"
        class="ml-auto p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-800 transition-colors"
        :class="
          contextRefreshing
            ? 'text-amber-500'
            : 'text-slate-400 dark:text-slate-500 hover:text-slate-700 dark:hover:text-white'
        "
        :disabled="contextLoading || contextRefreshing"
        title="Refresh network context"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="h-4 w-4"
          :class="{ 'animate-spin': contextRefreshing }"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="2"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
          />
        </svg>
      </button>
      <!-- Context toggle -->
      <button
        @click="includeContext = !includeContext"
        class="text-xs px-2 py-0.5 rounded-md font-medium transition-colors"
        :class="
          includeContext
            ? 'text-emerald-700 dark:text-emerald-400 bg-emerald-100 dark:bg-emerald-500/10'
            : 'text-slate-500 bg-slate-200 dark:bg-slate-800'
        "
        :disabled="contextLoading"
      >
        {{ includeContext ? 'Context ON' : 'Context OFF' }}
      </button>
    </div>

    <!-- Rate Limit Banner -->
    <div
      v-if="rateLimited"
      class="px-4 py-3 bg-amber-50 dark:bg-amber-900/20 border-t border-amber-200 dark:border-amber-800/50 flex items-center gap-3"
    >
      <div
        class="flex-shrink-0 w-8 h-8 rounded-full bg-amber-100 dark:bg-amber-900/40 flex items-center justify-center"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="h-4 w-4 text-amber-600 dark:text-amber-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="2"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      </div>
      <div class="flex-1">
        <p class="text-sm font-medium text-amber-800 dark:text-amber-200">Daily limit reached</p>
        <p class="text-xs text-amber-600 dark:text-amber-400">
          {{
            rateLimitMessage ||
            'You have used all your assistant chats for today. Your limit will reset at midnight.'
          }}
        </p>
      </div>
    </div>

    <!-- Input Area -->
    <div
      class="p-3 border-t border-slate-200/80 dark:border-slate-800/80 bg-slate-50 dark:bg-slate-950/50"
    >
      <form @submit.prevent="handleSubmit" class="flex gap-2 items-center">
        <input
          v-model="inputMessage"
          type="text"
          :placeholder="
            rateLimited ? 'Chat limit reached - try again tomorrow' : 'Ask about your network...'
          "
          class="flex-1 bg-white dark:bg-slate-800/60 border border-slate-300 dark:border-slate-700 rounded-lg px-4 py-2 text-slate-800 dark:text-white placeholder-slate-400 focus:border-violet-500 focus:ring-2 focus:ring-violet-500/20 outline-none text-sm transition-shadow disabled:bg-slate-100 dark:disabled:bg-slate-900 disabled:cursor-not-allowed"
          :disabled="inputDisabled"
          @keydown.enter.exact.prevent="handleSubmit"
        />
        <!-- Remaining chats indicator -->
        <span
          v-if="rateLimitInfo && !rateLimited"
          class="text-xs whitespace-nowrap"
          :class="[
            rateLimitInfo.is_exempt
              ? 'text-emerald-500 dark:text-emerald-400'
              : rateLimitInfo.remaining <= 3
                ? 'text-amber-500 dark:text-amber-400'
                : 'text-slate-400 dark:text-slate-500',
          ]"
          :title="
            rateLimitInfo.is_exempt
              ? 'Unlimited chats (exempt role)'
              : `${rateLimitInfo.used} of ${rateLimitInfo.limit} daily chats used`
          "
        >
          {{ rateLimitInfo.is_exempt ? '∞' : `${rateLimitInfo.remaining} left` }}
        </span>
        <button
          type="submit"
          :disabled="!inputMessage.trim() || inputDisabled"
          class="px-4 py-2 bg-gradient-to-r from-violet-600 to-fuchsia-600 hover:from-violet-500 hover:to-fuchsia-500 disabled:from-slate-400 disabled:to-slate-400 dark:disabled:from-slate-700 dark:disabled:to-slate-700 disabled:cursor-not-allowed rounded-lg text-white font-medium transition-all shadow-sm shadow-violet-500/20"
          :title="rateLimited ? 'Daily limit reached' : ''"
        >
          <svg
            v-if="!isStreaming"
            xmlns="http://www.w3.org/2000/svg"
            class="h-5 w-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5"
            />
          </svg>
          <svg
            v-else
            xmlns="http://www.w3.org/2000/svg"
            class="h-5 w-5 animate-spin"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
        </button>
      </form>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue';
import * as assistantApi from '../api/assistant';
import { marked } from 'marked';
import { apiUrl } from '../config';

// Props for network context
const props = defineProps<{
  networkId?: string;
}>();

const emit = defineEmits(['close']);

// Cloud deployment detection - hide model/provider selection and force Claude Haiku
const isCloudDeployment = (import.meta.env.BASE_URL || '/').startsWith('/app');
const CLOUD_PROVIDER = 'anthropic';
const CLOUD_MODEL = 'claude-haiku-4-5-20251001';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

interface Provider {
  provider: string;
  available: boolean;
  default_model?: string;
  available_models?: string[];
}

interface ContextSummary {
  total_nodes: number;
  healthy_nodes: number;
  unhealthy_nodes: number;
  gateway_count: number;
  loading?: boolean;
  unavailable?: boolean;
}

interface ContextStatus {
  snapshot_available: boolean;
  loading: boolean;
  ready: boolean;
}

const messages = ref<ChatMessage[]>([]);
const inputMessage = ref('');
const isStreaming = ref(false);
const currentStreamContent = ref('');
const error = ref<string | null>(null);
const messagesContainer = ref<HTMLElement | null>(null);

const selectedProvider = ref('openai');
const selectedModel = ref('');
const allProviders = ref<Provider[]>([]);
const availableProviders = ref<Provider[]>([]);
const userDefaultProvider = ref<string | null>(null);
const defaultProviderNotification = ref<string | null>(null);
const includeContext = ref(true);
const contextSummary = ref<ContextSummary | null>(null);
const contextLoading = ref(true);
const contextRefreshing = ref(false);
const contextStatusPollInterval = ref<number | null>(null);

// Rate limit state
const rateLimited = ref(false);
const rateLimitMessage = ref<string | null>(null);
const rateLimitInfo = ref<{
  used: number;
  limit: number;
  remaining: number;
  resets_in_seconds: number;
  is_exempt?: boolean;
} | null>(null);

// Computed: whether input should be disabled
const inputDisabled = computed(() => isStreaming.value || rateLimited.value);

// Computed property for current provider's models
const currentProviderModels = computed(() => {
  const provider = availableProviders.value.find((p) => p.provider === selectedProvider.value);
  return provider?.available_models || [];
});

const providerLabels: Record<string, string> = {
  openai: 'OpenAI',
  anthropic: 'Claude',
  gemini: 'Gemini',
  ollama: 'Ollama',
};

function getCookieValue(name: string): string | null {
  const prefix = `${name}=`;
  const cookie = document.cookie
    .split(';')
    .map((part) => part.trim())
    .find((part) => part.startsWith(prefix));
  if (!cookie) return null;
  return decodeURIComponent(cookie.slice(prefix.length));
}

// Check rate limit status proactively
async function checkRateLimitStatus() {
  try {
    const data = await assistantApi.getRateLimitStatus();

    // Store the full rate limit info
    rateLimitInfo.value = {
      used: (data as { used?: number }).used ?? 0,
      limit: data.limit,
      remaining: data.remaining,
      resets_in_seconds: (data as { resets_in_seconds?: number }).resets_in_seconds ?? 0,
      is_exempt: (data as { is_exempt?: boolean }).is_exempt || false,
    };

    // Exempt users never get rate limited
    if (rateLimitInfo.value.is_exempt) {
      rateLimited.value = false;
      rateLimitMessage.value = null;
    } else if (data.is_limited) {
      rateLimited.value = true;
      rateLimitMessage.value = `You've used all ${data.limit} daily chats. Resets in ${formatTimeUntilReset(rateLimitInfo.value.resets_in_seconds)}.`;
    } else {
      rateLimited.value = false;
      rateLimitMessage.value = null;
    }
  } catch (err: unknown) {
    // If we get a 429, we're rate limited
    const axiosError = err as { response?: { status?: number; data?: { detail?: string } } };
    if (axiosError.response?.status === 429) {
      rateLimited.value = true;
      rateLimitMessage.value =
        axiosError.response?.data?.detail ||
        'Daily chat limit exceeded. Please try again tomorrow.';
    } else {
      // Don't block the UI for other errors, just log
      console.error('Failed to check rate limit status:', err);
    }
  }
}

// Format seconds until reset as human-readable
function formatTimeUntilReset(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);

  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  return `${minutes}m`;
}

const suggestions = [
  "What's the health of my network?",
  'Are there any unhealthy devices?',
  'Show me my gateways',
  'Explain my network topology',
];

// Fetch available providers on mount
onMounted(async () => {
  loadDefaultProvider();
  await Promise.all([fetchProviders(), fetchContext(), checkRateLimitStatus()]);
});

// Cleanup polling on unmount
onUnmounted(() => {
  stopContextStatusPolling();
});

async function fetchProviders() {
  // In cloud deployment, force Anthropic/Claude Haiku - skip provider discovery
  if (isCloudDeployment) {
    selectedProvider.value = CLOUD_PROVIDER;
    selectedModel.value = CLOUD_MODEL;
    return;
  }

  try {
    const config = await assistantApi.getAssistantConfig();
    const providers = config.providers || [];

    // Store all providers for display
    allProviders.value = providers;
    // Filter available providers for selection
    availableProviders.value = providers.filter((p: Provider) => p.available);

    // Determine which provider to select
    let providerToSelect = null;

    // 1. Try user's saved default if it's available
    if (userDefaultProvider.value) {
      const userDefault = availableProviders.value.find(
        (p) => p.provider === userDefaultProvider.value
      );
      if (userDefault) {
        providerToSelect = userDefault;
      }
    }

    // 2. Fall back to first available provider
    if (!providerToSelect && availableProviders.value.length > 0) {
      providerToSelect = availableProviders.value[0];
    }

    // Set the selected provider and model
    if (providerToSelect) {
      selectedProvider.value = providerToSelect.provider;
      selectedModel.value =
        providerToSelect.default_model || providerToSelect.available_models?.[0] || '';
    }
  } catch (err) {
    console.error('Failed to fetch providers:', err);
    // Default to OpenAI if we can't fetch
    const defaultProvider = { provider: 'openai', available: true, default_model: 'gpt-4o-mini' };
    allProviders.value = [defaultProvider];
    availableProviders.value = [defaultProvider];
    selectedModel.value = 'gpt-4o-mini';
  }
}

function loadDefaultProvider() {
  try {
    const stored = localStorage.getItem('cartographer_default_provider');
    if (stored) {
      userDefaultProvider.value = stored;
    }
  } catch (e) {
    console.error('Failed to load default provider:', e);
  }
}

function setDefaultProvider(providerName: string) {
  try {
    userDefaultProvider.value = providerName;
    localStorage.setItem('cartographer_default_provider', providerName);

    // Show notification
    const providerLabel = providerLabels[providerName] || providerName;
    defaultProviderNotification.value = `${providerLabel} set as default`;

    // Clear notification after 3 seconds
    setTimeout(() => {
      defaultProviderNotification.value = null;
    }, 3000);
  } catch (e) {
    console.error('Failed to save default provider:', e);
  }
}

function getProviderTitle(p: Provider): string {
  const label = providerLabels[p.provider] || p.provider;
  if (!p.available) {
    return `${label} (unavailable)`;
  }
  if (p.provider === userDefaultProvider.value) {
    return `${label} (your default - double-click to change)`;
  }
  return `${label} (double-click to set as default)`;
}

function onProviderChange() {
  // Update model to the new provider's default
  const provider = availableProviders.value.find((p) => p.provider === selectedProvider.value);
  if (provider) {
    selectedModel.value = provider.default_model || provider.available_models?.[0] || '';
  }
}

function selectProvider(providerName: string) {
  if (isStreaming.value) return;
  selectedProvider.value = providerName;
  onProviderChange();
}

function formatModelName(model: string): string {
  // Shorten long model names for display
  if (model.length <= 25) return model;

  // Keep important parts visible
  const parts = model.split('-');
  if (parts.length >= 3) {
    // e.g., "claude-3-5-sonnet-20241022" -> "claude-3-5-sonnet"
    // Check if last part is a date
    const lastPart = parts[parts.length - 1];
    if (/^\d{8}$/.test(lastPart)) {
      return parts.slice(0, -1).join('-');
    }
  }

  return model.slice(0, 22) + '...';
}

async function fetchContext() {
  try {
    const data = await assistantApi.getContext(props.networkId);
    contextSummary.value = data as ContextSummary;

    // Check if context is actually available or loading
    const contextData = data as { loading?: boolean; total_nodes?: number };
    if (contextData.loading || contextData.total_nodes === 0) {
      contextLoading.value = true;
      // Start polling for context status
      startContextStatusPolling();
    } else {
      contextLoading.value = false;
      stopContextStatusPolling();
    }
  } catch (err) {
    console.error('Failed to fetch context:', err);
    contextLoading.value = true;
    startContextStatusPolling();
  }
}

async function fetchContextStatus() {
  try {
    const data = await assistantApi.getContextStatus(props.networkId);
    const status: ContextStatus = {
      snapshot_available: (data as { snapshot_available?: boolean }).snapshot_available ?? false,
      loading: !data.needs_refresh,
      ready: !data.needs_refresh,
    };

    if (status.ready && status.snapshot_available) {
      contextLoading.value = false;
      stopContextStatusPolling();
      // Refresh the full context
      await fetchContext();
    }
  } catch (err) {
    console.error('Failed to fetch context status:', err);
  }
}

function startContextStatusPolling() {
  if (contextStatusPollInterval.value) return; // Already polling

  contextStatusPollInterval.value = window.setInterval(() => {
    fetchContextStatus();
  }, 5000); // Poll every 5 seconds
}

function stopContextStatusPolling() {
  if (contextStatusPollInterval.value) {
    clearInterval(contextStatusPollInterval.value);
    contextStatusPollInterval.value = null;
  }
}

async function refreshContext() {
  if (contextRefreshing.value) return;

  contextRefreshing.value = true;
  try {
    await assistantApi.refreshContext(props.networkId);
    // Then fetch the updated context
    await fetchContext();
  } catch (err) {
    console.error('Failed to refresh context:', err);
  } finally {
    contextRefreshing.value = false;
  }
}

// Configure marked for chat messages
marked.setOptions({
  breaks: true, // Convert \n to <br>
  gfm: true, // GitHub Flavored Markdown
});

function formatMessage(content: string): string {
  // Use marked to parse markdown
  const html = marked.parse(content, { async: false }) as string;
  return html;
}

async function sendMessage(content: string) {
  inputMessage.value = content;
  await handleSubmit();
}

async function handleSubmit() {
  const message = inputMessage.value.trim();
  if (!message || isStreaming.value) return;

  // Clear input and error
  inputMessage.value = '';
  error.value = null;

  // Add user message
  messages.value.push({ role: 'user', content: message });
  scrollToBottom();

  // Start streaming
  isStreaming.value = true;
  currentStreamContent.value = '';

  try {
    // Build conversation history (exclude current message)
    const history = messages.value.slice(0, -1).map((m) => ({
      role: m.role,
      content: m.content,
    }));

    const csrfToken = getCookieValue('cartographer_csrf');

    const response = await fetch(apiUrl('/api/assistant/chat/stream'), {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        ...(csrfToken ? { 'X-CSRF-Token': csrfToken } : {}),
      },
      body: JSON.stringify({
        message,
        provider: isCloudDeployment ? CLOUD_PROVIDER : selectedProvider.value,
        model: isCloudDeployment ? CLOUD_MODEL : selectedModel.value || undefined,
        conversation_history: history,
        include_network_context: includeContext.value,
        network_id: props.networkId,
      }),
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      const errorMessage = errData.detail || `HTTP ${response.status}`;

      // Check for rate limit (429)
      if (response.status === 429) {
        rateLimited.value = true;
        const limitMsg = errorMessage.includes('Daily')
          ? errorMessage
          : 'Daily chat limit exceeded. Please try again tomorrow.';
        rateLimitMessage.value = limitMsg;
        throw new Error(limitMsg);
      }

      throw new Error(errorMessage);
    }

    const reader = response.body?.getReader();
    if (!reader) throw new Error('No response body');

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));

            if (data.type === 'content') {
              currentStreamContent.value += data.content;
              scrollToBottom();
            } else if (data.type === 'context') {
              // Update context summary if provided
              if (data.summary) {
                contextSummary.value = data.summary;
              }
            } else if (data.type === 'error') {
              error.value = data.error;
            } else if (data.type === 'done') {
              // Streaming complete
            }
          } catch (e) {
            // Ignore JSON parse errors for incomplete chunks
          }
        }
      }
    }

    // Add assistant message
    if (currentStreamContent.value) {
      messages.value.push({ role: 'assistant', content: currentStreamContent.value });
    }
  } catch (err: any) {
    console.error('Chat error:', err);
    error.value = err.message || 'Failed to get response';
  } finally {
    isStreaming.value = false;
    currentStreamContent.value = '';
    scrollToBottom();
    // Refresh rate limit status after each chat attempt
    checkRateLimitStatus();
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
    }
  });
}

// Auto-scroll when messages change
watch(messages, scrollToBottom, { deep: true });
</script>

<style scoped>
/* Custom scrollbar - light mode */
.overflow-y-auto::-webkit-scrollbar {
  width: 6px;
}
.overflow-y-auto::-webkit-scrollbar-track {
  background: transparent;
}
.overflow-y-auto::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}
.overflow-y-auto::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

/* Custom scrollbar - dark mode */
:root.dark .overflow-y-auto::-webkit-scrollbar-thumb {
  background: #475569;
}
:root.dark .overflow-y-auto::-webkit-scrollbar-thumb:hover {
  background: #64748b;
}

/* Prose base styles for assistant messages */
.prose :deep(code) {
  color: #1e293b;
  background: #f1f5f9;
  padding: 0.125rem 0.25rem;
  border-radius: 0.25rem;
  font-size: 0.875em;
}
.prose :deep(pre) {
  background: #f1f5f9;
  padding: 0.75rem;
  border-radius: 0.375rem;
  overflow-x: auto;
  margin: 0.5rem 0;
}
.prose :deep(pre code) {
  background: transparent;
  padding: 0;
}
.prose :deep(p) {
  margin: 0.5rem 0;
}
.prose :deep(p:first-child) {
  margin-top: 0;
}
.prose :deep(p:last-child) {
  margin-bottom: 0;
}
.prose :deep(ul),
.prose :deep(ol) {
  margin: 0.5rem 0;
  padding-left: 1.5rem;
}
.prose :deep(li) {
  margin: 0.25rem 0;
}
.prose :deep(ul) {
  list-style-type: disc;
}
.prose :deep(ol) {
  list-style-type: decimal;
}
.prose :deep(a) {
  color: #7c3aed;
  text-decoration: underline;
}
.prose :deep(a:hover) {
  color: #6d28d9;
}
.prose :deep(blockquote) {
  border-left: 3px solid #8b5cf6;
  padding-left: 0.75rem;
  margin: 0.5rem 0;
  color: #475569;
}
.prose :deep(h1),
.prose :deep(h2),
.prose :deep(h3),
.prose :deep(h4) {
  font-weight: 600;
  margin: 0.75rem 0 0.5rem 0;
}
.prose :deep(h1) {
  font-size: 1.25rem;
}
.prose :deep(h2) {
  font-size: 1.125rem;
}
.prose :deep(h3) {
  font-size: 1rem;
}
.prose :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 0.5rem 0;
}
.prose :deep(th),
.prose :deep(td) {
  border: 1px solid #e2e8f0;
  padding: 0.375rem 0.5rem;
  text-align: left;
}
.prose :deep(th) {
  background: #f8fafc;
  font-weight: 600;
}
.prose :deep(hr) {
  border: none;
  border-top: 1px solid #e2e8f0;
  margin: 0.75rem 0;
}

/* Prose overrides for dark mode - assistant messages */
.prose.dark\:prose-invert :deep(code) {
  color: #e2e8f0;
  background: #0f172a;
}
.prose.dark\:prose-invert :deep(pre) {
  background: #0f172a;
}
.prose.dark\:prose-invert :deep(a) {
  color: #a78bfa;
}
.prose.dark\:prose-invert :deep(a:hover) {
  color: #c4b5fd;
}
.prose.dark\:prose-invert :deep(blockquote) {
  border-left-color: #8b5cf6;
  color: #cbd5e1;
}
.prose.dark\:prose-invert :deep(th),
.prose.dark\:prose-invert :deep(td) {
  border-color: #475569;
}
.prose.dark\:prose-invert :deep(th) {
  background: #1e293b;
}
.prose.dark\:prose-invert :deep(hr) {
  border-top-color: #475569;
}

/* User message prose - lighter code backgrounds for violet bubble */
.prose-user :deep(code) {
  background: rgba(0, 0, 0, 0.2);
}
.prose-user :deep(pre) {
  background: rgba(0, 0, 0, 0.25);
}
.prose-user :deep(a) {
  color: #e0e7ff;
}
.prose-user :deep(a:hover) {
  color: #ffffff;
}
.prose-user :deep(blockquote) {
  border-left-color: #c4b5fd;
  color: #e0e7ff;
}
</style>
