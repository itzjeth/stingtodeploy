const faqAdditionalQuestions = document.querySelector('.t-faq__more');
  const showMoreFaq = document.querySelector('.t-faq__more-trigger');
  const showMoreTexts = document.querySelectorAll('.t-faq__more-text');
  showMoreFaq.addEventListener('click', () => {
    faqAdditionalQuestions.classList.toggle('u-hidden')
    for (const text of showMoreTexts) {
      text.classList.toggle('u-hidden')
    }
  });